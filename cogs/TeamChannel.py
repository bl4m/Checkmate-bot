import asyncio
import random
from collections.abc import Mapping
from logging import getLogger
from os import getenv, path
from typing import Any

import discord
from discord.ext import commands

from database import db_manager
from settings import ADMIN_ROLE, CATEGORY_NAME
from views import TeamChannelButton

logger = getLogger(__name__)

KABOOM = discord.File(path.join("assets", "Kaboom.jpg"), filename="Kaboom.jpg")


assert db_manager is not None, "Database not found!"
assert ADMIN_ROLE is not None, "Admin role not found!"


class TeamChannels(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._invalid_ids = []
        self._not_in_guild = []
        self._creating = False

        self.bot.add_view(TeamChannelButton())

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
        sql = 'SELECT "Discord" FROM "Somnium" WHERE "Team Name" = $1'
        rows = await db_manager.fetch_all(sql, team)
        players = [row["Discord"] for row in rows]

        # Resolve members from DB
        resolved_members = await asyncio.gather(
            *[self.resolve_player(p, guild) for p in players]
        )
        resolved_members = list(filter(None, resolved_members))

        # Check if VC already exists
        normalized_team_name = team.strip().lower().replace(" ", "-")
        existing_channel = discord.utils.get(
            guild.voice_channels, name=normalized_team_name
        )

        if existing_channel:
            # Cleanup old permissions
            cleanup_tasks = [
                existing_channel.set_permissions(target, overwrite=None)
                for target in existing_channel.overwrites
                if isinstance(target, discord.Member) and target not in resolved_members
            ]
            update_tasks = [
                existing_channel.set_permissions(
                    member,
                    overwrite=discord.PermissionOverwrite(
                        view_channel=True, connect=True
                    ),
                )
                for member in resolved_members
            ]
            await asyncio.gather(*cleanup_tasks, *update_tasks)
            return

        # Build overwrites for team members
        overwrites: Mapping[Any, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, connect=False
            )
        }
        for member in resolved_members:
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True, connect=True
            )

        # Find a category with < 50 voice channels
        def get_or_create_category_slot(
            guild: discord.Guild, base_name: str = CATEGORY_NAME
        ):
            for category in guild.categories:
                if (
                    category.name.startswith(base_name)
                    and len(category.voice_channels) < 50
                ):
                    return category
            return None

        category = get_or_create_category_slot(guild)

        # If no suitable category, make a new one
        if category is None:
            count = sum(1 for c in guild.categories if c.name.startswith(CATEGORY_NAME))
            category = await guild.create_category(
                name=f"CHECKMATE VOICE CHANNELS #{count + 1}",
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=False, connect=False
                    )
                },
            )

        # Create VC
        await guild.create_voice_channel(
            name=normalized_team_name,
            category=category,
            overwrites=overwrites,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        candidates = []
        for value in (member.name, member.global_name, str(member.id)):
            if value and value not in candidates:
                candidates.append(value)

        result = None
        for candidate in candidates:
            result = await db_manager.fetch_row(
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

        guild = self.bot.guilds[0]
        team_name = str(team_name).strip()
        normalized_team_name = team_name.lower().replace(" ", "-")

        role_name = f"team-{normalized_team_name}"
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role is None:
            colors = [
                discord.Color.red(),
                discord.Color.blue(),
                discord.Color.green(),
                discord.Color.gold(),
                discord.Color.purple(),
                discord.Color.orange(),
                discord.Color.teal(),
                discord.Color.magenta(),
            ]
            color = random.choice(colors)
            existing_role = await guild.create_role(
                name=role_name,
                color=color,
                reason=f"Role for {team_name} team",
                mentionable=True,
            )

        if member not in existing_role.members:
            await member.add_roles(existing_role, reason=f"Joined team {team_name}")

        voice_channel = discord.utils.get(
            guild.voice_channels, name=normalized_team_name
        )

        if voice_channel is None:
            await self._create_voice_channel(team_name, guild)
        else:
            # Set permission for the user
            overwrite = discord.PermissionOverwrite()
            overwrite.view_channel = True
            overwrite.connect = True
            await voice_channel.set_permissions(member, overwrite=overwrite)

    # @commands.hybrid_command(name="create-vc")
    # @commands.has_role(ADMIN_ROLE)
    # async def create_channels(self, ctx: commands.Context, team_name: str):
    #     """
    #     Just pass the entire teams collection to this
    #     """

    #     if self._creating:
    #         return

    #     if ctx.interaction:
    #         await ctx.interaction.response.defer(ephemeral=True)

    #     if not self.bot.guilds:
    #         raise RuntimeError("Bot is not in any guild")

    #     self._creating = True

    #     # Waits till bot is running
    #     await self.bot.wait_until_ready()

    #     # Gets the discord server
    #     guild = self.bot.guilds[0]

    #     team: dict[str, Any] | None = await teams.find_one({"team_name": team_name})

    #     if team is None:
    #         if ctx.interaction:
    #             await ctx.interaction.response.send_message(
    #                 "Team name is wrong or team not registered/not found",
    #                 ephemeral=True,
    #                 delete_after=5,
    #             )
    #         else:
    #             await ctx.reply(
    #                 "Team name is wrong or team not found/registered",
    #                 ephemeral=True,
    #                 delete_after=5,
    #             )
    #         return

    #     await self._create_voice_channel(team, guild)

    #     reply_text = "Created voice channels, Here are the invalid IDs and the people who did not join this fucking discord server and made my blood boil"
    #     invalid_id_text = "\n".join(self._invalid_ids)
    #     not_in_guild_id_text = "\n".join(self._not_in_guild)

    #     if ctx.interaction:
    #         await ctx.interaction.followup.send(reply_text, ephemeral=True)
    #         await ctx.interaction.followup.send(invalid_id_text, ephemeral=True)
    #         await ctx.interaction.followup.send(not_in_guild_id_text, ephemeral=True)

    #     else:
    #         await ctx.reply(reply_text, ephemeral=True)
    #         await ctx.author.send(invalid_id_text)
    #         await ctx.author.send(not_in_guild_id_text)

    #     self._creating = False

    @commands.hybrid_command(name="delete_somnium_vcs")
    @commands.has_role(ADMIN_ROLE)
    async def delete_somnium_vcs(self, ctx: commands.Context):
        """
        Deletes all voice channels in categories starting with the configured Somnium category name.
        """
        guild = ctx.guild

        if not guild:
            logger.exception("Bot not in any guild!")
            return

        if not guild.categories:
            logger.exception("The fuck, no categories found??")
            return

        await ctx.reply(file=KABOOM)
        # Filter categories that match
        target_categories = [
            category
            for category in guild.categories
            if category.name.startswith(CATEGORY_NAME)
        ]

        if not target_categories:
            await ctx.reply("No matching categories found.", ephemeral=True)
            return

        # Loop through each category and delete its voice channels
        for category in target_categories:
            for channel in category.voice_channels:
                try:
                    await channel.delete()
                    await asyncio.sleep(0.5)  # to avoid hitting rate limits
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to delete {channel.name}: {e}")

        await ctx.reply("Deleted voice channels.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamChannels(bot))
