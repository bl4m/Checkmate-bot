from __future__ import annotations

from typing import Any, Optional

from .database import PostgresManager


db_manager: Optional[PostgresManager] = None


def get_db() -> PostgresManager:
    """Always read the pool through this.

    Importing ``db_manager`` by value at module scope captures whatever it was
    at import time (usually ``None``) and never sees a pool created later.
    """
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return db_manager


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
        db = get_db()

        if team_name is None:
            rows = await db.fetch_all(
                'SELECT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" ORDER BY "Team Name", "Discord"'
            )
        else:
            rows = await db.fetch_all(
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

    async def _team_document_for_member(self, target: str):
        rows = await get_db().fetch_all(
            'SELECT DISTINCT "Team Name" AS team_name, "Discord" AS discord FROM "Somnium" WHERE "Discord" = $1 ORDER BY "Team Name"',
            target,
        )
        if not rows:
            return None

        team_name = str(rows[0]["team_name"])
        # Re-read the whole team, otherwise the document only contains the one
        # member we searched for.
        return await self._team_document_for_name(team_name)

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
                    document = await self._team_document_for_member(
                        str(criterion["players.discord_id"])
                    )
                    if document is not None:
                        return document

        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any]):
        db = get_db()

        team_name = query.get("team_name") or query.get("_id")
        if team_name is None:
            return {"matched_count": 0, "modified_count": 0}

        if "$set" in update and "players" in update["$set"]:
            players = update["$set"]["players"]
            await db.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
            await self._insert_players(str(team_name), players)
            return {"matched_count": 1, "modified_count": 1}

        if "$push" in update and "players" in update["$push"]:
            push = update["$push"]["players"]
            new_players = (
                push["$each"] if isinstance(push, dict) and "$each" in push else [push]
            )
            existing = await self._team_document_for_name(str(team_name))
            if existing is None:
                return {"matched_count": 0, "modified_count": 0}
            added = await self._insert_players(str(team_name), new_players)
            return {"matched_count": 1, "modified_count": 1 if added else 0}

        return {"matched_count": 0, "modified_count": 0}

    async def _insert_players(self, team_name: str, players: list[dict[str, Any]]) -> int:
        db = get_db()
        inserted = 0
        for player in players:
            member_id = (
                player.get("discord_id") or player.get("Discord") or player.get("discord")
                if isinstance(player, dict)
                else player
            )
            if member_id is None:
                continue
            await db.execute(
                'INSERT INTO "Somnium" ("Team Name", "Discord") VALUES ($1, $2)',
                team_name,
                str(member_id),
            )
            inserted += 1
        return inserted

    async def delete_one(self, query: dict[str, Any]):
        db = get_db()

        team_name = query.get("team_name") or query.get("_id")
        if not team_name:
            return {"deleted_count": 0}

        await db.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
        return {"deleted_count": 1}

    async def insert_one(self, document: dict[str, Any]):
        db = get_db()

        team_name = document.get("team_name") or document.get("_id")
        players = document.get("players", [])
        if team_name is None:
            return None

        await db.execute('DELETE FROM "Somnium" WHERE "Team Name" = $1', str(team_name))
        await self._insert_players(str(team_name), players)
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
