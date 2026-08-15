from logging import getLogger

import asyncpg
import discord

from database import get_db
from guild_utils import ensure_team_voice_channel, get_or_create_team_role
from settings import EVENT_NAME
from views.utils import create_success_embed

logger = getLogger(__name__)


class TeamChannelButton(discord.ui.View):
    def __init__(self, *, timeout: float | None = None):
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
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return

        guild = interaction.guild

        # Creating a role and a channel can take longer than the 3s interaction
        # window, so acknowledge first and follow up afterwards.
        await interaction.response.defer(ephemeral=True)

        sql = """
            SELECT "Team Name" AS team_name
            FROM "Somnium"
            WHERE "Discord" = $1 OR "Discord" = $2
            LIMIT 1
        """

        team: asyncpg.Record | None = await get_db().fetch_row(
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

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        team_name = str(team["team_name"]).strip()

        role = await get_or_create_team_role(guild, team_name)

        if role is not None and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role, reason=f"Joined team {team_name}")
            except discord.HTTPException:
                logger.exception("Could not add %s to role %s", interaction.user.id, role.name)

        # Grant this member access explicitly. Relying on the team role alone
        # was the old bug: the channel had no overwrite for the role either, so
        # nobody could see the channel they had just been given.
        channel = await ensure_team_voice_channel(
            guild, team_name, [interaction.user], role
        )

        if channel is None:
            await interaction.followup.send(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    title="Could not set up your voice channel",
                    description="Please contact CORE so we can sort this out for you.",
                ),
                ephemeral=True,
            )
            return

        embed = create_success_embed(
            f"You have been added to team: {team_name}. "
            f"Please use {channel.mention} as your mode of communication."
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
