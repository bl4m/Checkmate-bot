from __future__ import annotations

from typing import Any, Optional

from .database import PostgresManager


db_manager: Optional[PostgresManager] = None


class PostgresTeamCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._rows):
            raise StopAsyncIteration
        row = self._rows[self._index]
        self._index += 1
        return row

    async def to_list(self, length: int | None = None):
        rows = self._rows if length is None else self._rows[:length]
        return rows


class PostgresTeamsAdapter:
    async def _get_team_rows(self, team_name: str | None = None):
        if db_manager is None:
            raise RuntimeError("Database not initialized.")

        if team_name is None:
            rows = await db_manager.fetch_all(
                'SELECT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" ORDER BY "Team Name", "Discord"'
            )
        else:
            rows = await db_manager.fetch_all(
                'SELECT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" WHERE "Team Name" = $1 ORDER BY "Discord"',
                team_name,
            )
        return list(rows)

    def _rebuild_team_document(self, team_name: str, members: list[str]) -> dict[str, Any]:
        players = [
            {
                "discord_id": str(member),
                "is_hacker": False,
                "is_wizard": False,
            }
            for member in members
            if member is not None
        ]
        return {
            "_id": team_name,
            "team_name": team_name,
            "players": players,
        }

    async def _team_document_for_name(self, team_name: str):
        rows = await self._get_team_rows(team_name)
        if not rows:
            return None
        members = [str(row["discord"]) for row in rows if row.get("discord") is not None]
        return self._rebuild_team_document(team_name, members)

    async def find(self, query: dict[str, Any] | None = None):
        query = query or {}
        if query == {}:
            rows = await self._get_team_rows()
            grouped: dict[str, list[str]] = {}
            for row in rows:
                team_name = str(row["team_name"])
                discord_name = row.get("discord")
                grouped.setdefault(team_name, [])
                if discord_name is not None:
                    grouped[team_name].append(str(discord_name))
            documents = [
                self._rebuild_team_document(team_name, members)
                for team_name, members in grouped.items()
            ]
            return PostgresTeamCursor(documents)
        if "team_name" in query:
            team_name = query["team_name"]
            doc = await self._team_document_for_name(team_name)
            return PostgresTeamCursor([doc] if doc else [])
        return PostgresTeamCursor([])

    async def find_one(self, query: dict[str, Any] | None = None):
        query = query or {}

        if "team_name" in query:
            return await self._team_document_for_name(str(query["team_name"]))

        if "$or" in query:
            for criterion in query["$or"]:
                if "players.discord_id" in criterion:
                    target = str(criterion["players.discord_id"])
                    rows = await db_manager.fetch_all(
                        'SELECT DISTINCT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" WHERE "Discord" = $1 ORDER BY "Team Name"',
                        target,
                    )
                    if rows:
                        grouped: dict[str, list[str]] = {}
                        for row in rows:
                            grouped.setdefault(str(row["team_name"]), []).append(str(row["discord"]))
                        team_name = next(iter(grouped))
                        return self._rebuild_team_document(team_name, grouped[team_name])
                if "players.discord_id" in criterion:
                    target = str(criterion["players.discord_id"])
                    rows = await db_manager.fetch_all(
                        'SELECT DISTINCT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" WHERE "Discord" = $1 ORDER BY "Team Name"',
                        target,
                    )
                    if rows:
                        grouped: dict[str, list[str]] = {}
                        for row in rows:
                            grouped.setdefault(str(row["team_name"]), []).append(str(row["discord"]))
                        team_name = next(iter(grouped))
                        return self._rebuild_team_document(team_name, grouped[team_name])

        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        if db_manager is None:
            raise RuntimeError("Database not initialized.")

        if "$set" in update and "players" in update["$set"]:
            team_name = query.get("team_name") or query.get("_id")
            if team_name is None:
                return {"matched_count": 0, "modified_count": 0}
            players = update["$set"]["players"]
            await db_manager.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
            for player in players:
                member_id = player.get("discord_id") or player.get("Discord") or player.get("discord")
                if member_id is not None:
                    await db_manager.execute(
                        'INSERT INTO "Somnium" ("Team Name", "Discord") VALUES ($1, $2)',
                        str(team_name),
                        str(member_id),
                    )
            return {"matched_count": 1, "modified_count": 1}
        return {"matched_count": 0, "modified_count": 0}

    async def delete_one(self, query: dict[str, Any]):
        if db_manager is None:
            raise RuntimeError("Database not initialized.")

        team_name = query.get("team_name") or query.get("_id")
        if not team_name:
            return {"deleted_count": 0}

        await db_manager.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
        return {"deleted_count": 1}

    async def insert_one(self, document: dict[str, Any]):
        if db_manager is None:
            raise RuntimeError("Database not initialized.")

        team_name = document.get("team_name") or document.get("_id")
        players = document.get("players", [])
        if team_name is None:
            return None

        await db_manager.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
        for player in players:
            member_id = player.get("discord_id") or player.get("Discord") or player.get("discord")
            if member_id is not None:
                await db_manager.execute(
                    'INSERT INTO "Somnium" ("Team Name", "Discord") VALUES ($1, $2)',
                    str(team_name),
                    str(member_id),
                )
        return {"inserted_id": team_name}


teams = PostgresTeamsAdapter()


async def init_db():
    """Initialize the PostgreSQL pool used throughout the bot."""
    global db_manager
    db_manager = await PostgresManager.create()


async def init_teams():
    """Compat for older Mongo-based startup code. For now, this just ensures the DB is initialized."""
    if db_manager is None:
        await init_db()
