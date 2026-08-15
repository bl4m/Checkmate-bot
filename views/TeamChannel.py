import random
from logging import getLogger
from typing import Any

import asyncpg
import discord
from discord import Member, PermissionOverwrite, Role

from database import db_manager
from settings import CATEGORY_NAME, EVENT_NAME
from views.utils import create_success_embed

logger = getLogger(__name__)
assert db_manager is not None, "database not found!"


class TeamChannelButton(discord.ui.View):
    def __init__(self, *, timeout: float | None = 180):
        super().__init__(timeout=None)

    @discord.ui.button(
        custom_id="click_button",
        label="Click here",
        style=discord.ButtonStyle.primary,
        emoji="🏳️",
    )
    async def on_click(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if not interaction.guild:
            return

        guild = interaction.guild

        sql = """
            SELECT "Team Name" AS team_name, "Discord" AS discord
            FROM "Somnium"
            WHERE "Discord" = $1 OR "Discord" = $2
            LIMIT 1
        """

        team: asyncpg.Record | None = await db_manager.fetch_row(
            sql,
            interaction.user.name.strip(),
            str(interaction.user.id),
        )


        if not team:
            embed = discord.Embed(
                color=discord.Color.red(),
                title="Team information not found!",
                description=f"Please make sure to register yourself for {EVENT_NAME} from the official registration portal.\n"
                + "If you have already registered, then most likely your Discord username or ID is incorrect.\n"
                + "You can edit it on the team dashboard on the registration portal.",
            ).set_footer(text="If the issue persists, please contact CORE")

            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            return

        raw_team_name = team.get("team_name") or team.get("Team Name") or team.get("team_name ")
        team_name = str(raw_team_name).strip()
        normalized_team_name = team_name.lower().replace(" ", "-")

        role_name = f"team-{normalized_team_name}"
        existing_role = discord.utils.get(interaction.guild.roles, name=role_name)
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
            existing_role = await interaction.guild.create_role(
                name=role_name,
                color=color,
                reason=f"Role for {team_name} team",
                mentionable=True,
            )

        if interaction.user not in existing_role.members:
            await interaction.user.add_roles(existing_role, reason=f"Joined team {team_name}")

        voice_channel = discord.utils.get(
            interaction.guild.voice_channels, name=normalized_team_name
        )

        if not voice_channel:
            overwrites: dict[Role | Member | discord.Object, PermissionOverwrite] = {
                interaction.guild.default_role: PermissionOverwrite(view_channel=False),
            }

            # Gets the Obscura category
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

            if category is None:
                category_overwrites: dict[
                    Role | Member | discord.Object, PermissionOverwrite
                ] = {
                    guild.default_role: PermissionOverwrite(
                        view_channel=False, connect=False
                    ),
                }
                category = await guild.create_category(
                    name=CATEGORY_NAME, overwrites=category_overwrites
                )

            # Creates a voice channel
            await guild.create_voice_channel(
                name=normalized_team_name, category=category, overwrites=overwrites
            )

        embed = create_success_embed(
            f"You have been added to team: {team_name}. Please use the voice channel as your mode of communication."
        )
        await interaction.response.send_message(
            embed=embed, ephemeral=True, delete_after=3
        )
