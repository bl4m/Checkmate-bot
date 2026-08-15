import asyncio
from collections.abc import Mapping
from logging import getLogger
from os import path
from typing import Any

import discord
from discord.ext import commands

from database import get_db
from guild_utils import (
    ensure_team_voice_channel,
    get_or_create_team_role,
    normalize_team_name,
)
from settings import ADMIN_ROLE, CATEGORY_NAME

logger = getLogger(__name__)

KABOOM_PATH = path.join("assets", "Kaboom.jpg")

assert ADMIN_ROLE is not None, "Admin role not found!"


class TeamChannels(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._invalid_ids: list[str] = []
        self._not_in_guild: list[str] = []
        self._creating = False

    @property
    def invalid_ids(self):
        """
        Returns all the ids that are invalid/not in guild.
        """

        return self._invalid_ids

    @property
    def not_in_guild(self):
        return self._not_in_guild

    # Get's each players discord id from db and edit perms accordingly
    async def resolve_player(self, player: dict[str, Any] | str, guild: discord.Guild):
        if isinstance(player, Mapping):
            raw_id = (
                str(player.get("discord_id") or player.get("Discord") or player.get("discord") or "")
            ).strip()
        else:
            raw_id = str(player or "").strip()

        if not raw_id:
            return None

        member = None

        try:
            # Discord id is in the form of int, can use to check if id is valid or not
            if raw_id.isdigit():
                member_id = int(raw_id)

                member = guild.get_member(member_id)
                if not member:
                    try:
                        member = await guild.fetch_member(member_id)
                    except discord.NotFound:
                        self._not_in_guild.append(raw_id)
                        return None

            else:
                # Discord id is a string, cannot use to check if id is valid or not
                username_input = raw_id.lower()
                member = next(
                    (
                        m
                        for m in guild.members
                        if m.name.lower() == username_input
                        or (m.global_name and m.global_name.lower() == username_input)
                    ),
                    None,
                )
                if not member:
                    self._invalid_ids.append(raw_id)
                    return None

            # Final check: validate user exists
            try:
                await self.bot.fetch_user(member.id)
            except discord.NotFound:
                self._invalid_ids.append(raw_id)
                return None

            return member

        except (discord.HTTPException, ValueError, TypeError):
            self._invalid_ids.append(raw_id)
            return None

    # Creates the voice channels and edit's their permission
    async def _create_voice_channel(self, team: str, guild: discord.Guild):
        # These are per-run diagnostics; without clearing they grew forever.
        self._invalid_ids.clear()
        self._not_in_guild.clear()

        sql = 'SELECT "Discord" FROM "Somnium" WHERE "Team Name" = $1'
        rows = await get_db().fetch_all(sql, team)
        players = [row["Discord"] for row in rows]

        # Resolve members from DB
        resolved_members = await asyncio.gather(
            *[self.resolve_player(p, guild) for p in players]
        )
        resolved_members = list(filter(None, resolved_members))

        role = await get_or_create_team_role(guild, team)

        # This is the whole roster, so stale member overwrites can be pruned.
        return await ensure_team_voice_channel(
            guild, team, resolved_members, role, prune=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        candidates = []
        for value in (member.name, member.global_name, str(member.id)):
            if value and value not in candidates:
                candidates.append(value)

        result = None
        for candidate in candidates:
            result = await get_db().fetch_row(
                'SELECT "Team Name" FROM "Somnium" WHERE "Discord" = $1',
                candidate,
            )
            if result:
                break

        if result:
            team_name = result.get("Team Name") or result.get("team_name")
            if team_name is None:
                logger.warning(
                    "Team lookup returned a row without a usable team name for %s (%s).",
                    member.name,
                    member.global_name,
                )
                return
            logger.info(f"User {member.name} ({member.global_name}) is in team: {team_name}")
        else:
            logger.warning(
                "Team not found for %s (%s) / %s; user may not be registered or username mismatch.",
                member.name,
                member.global_name,
                member.id,
            )
            return

        guild = member.guild
        team_name = str(team_name).strip()

        role = await get_or_create_team_role(guild, team_name)

        if role is not None and role not in member.roles:
            try:
                await member.add_roles(role, reason=f"Joined team {team_name}")
            except discord.HTTPException:
                logger.exception("Could not add %s to role %s", member.id, role.name)

        channel = discord.utils.get(
            guild.voice_channels, name=normalize_team_name(team_name)
        )

        if channel is None:
            # No channel yet: build it from the full roster.
            await self._create_voice_channel(team_name, guild)
        else:
            # Only this member is joining, so never prune the others.
            await ensure_team_voice_channel(guild, team_name, [member], role)

    @commands.hybrid_command(name="delete_somnium_vcs")
    @commands.has_role(ADMIN_ROLE)
    async def delete_somnium_vcs(self, ctx: commands.Context):
        """
        Deletes all voice channels in categories starting with the configured Somnium category name.
        """
        guild = ctx.guild

        if not guild:
            logger.error("delete_somnium_vcs called outside a guild.")
            return

        # Filter categories that match
        target_categories = [
            category
            for category in guild.categories
            if category.name.startswith(CATEGORY_NAME)
        ]

        if not target_categories:
            await ctx.reply("No matching categories found.", ephemeral=True)
            return

        # A discord.File is consumed once it is sent, so build a fresh one per call.
        await ctx.reply(file=discord.File(KABOOM_PATH, filename="Kaboom.jpg"))

        deleted = 0

        # Loop through each category and delete its voice channels
        for category in target_categories:
            for channel in category.voice_channels:
                try:
                    await channel.delete()
                    deleted += 1
                    await asyncio.sleep(0.5)  # to avoid hitting rate limits
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to delete {channel.name}: {e}")

        await ctx.send(f"Deleted {deleted} voice channel(s).", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamChannels(bot))
