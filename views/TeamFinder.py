from logging import getLogger

import aiosqlite
import discord

from database import teams
from settings import LFT_DB_PATH
from views.utils import create_failure_embed, create_success_embed

logger = getLogger(__name__)

LFT_DB = LFT_DB_PATH
MAX_TEAM_SIZE = 4


async def _is_marked_lft(discord_id: int) -> bool:
    async with aiosqlite.connect(LFT_DB) as db:
        cursor = await db.execute(
            "SELECT 1 FROM lft_users WHERE discord_id = ?", (discord_id,)
        )
        return await cursor.fetchone() is not None


async def _mark_lft(discord_id: int) -> None:
    async with aiosqlite.connect(LFT_DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO lft_users (discord_id) VALUES (?)", (discord_id,)
        )
        await db.commit()


async def _unmark_lft(discord_id: int) -> None:
    async with aiosqlite.connect(LFT_DB) as db:
        await db.execute("DELETE FROM lft_users WHERE discord_id = ?", (discord_id,))
        await db.commit()


class LookingForTeamView(discord.ui.View):
    def __init__(self, player_id):
        super().__init__()
        self.player_id = player_id
        self.selected_role = None

    @discord.ui.select(
        placeholder="Which role are you going to play?",
        options=[
            discord.SelectOption(label="💻 Hacker", value="hacker"),
            discord.SelectOption(label="🧙 Wizard", value="wizard"),
        ],
    )
    async def select_role(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        if not isinstance(interaction.channel, discord.TextChannel):
            return

        if interaction.user.id != self.player_id:
            embed = create_failure_embed("This isn't your LFT panel.")
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            return

        if await _is_marked_lft(interaction.user.id):
            embed = discord.Embed(
                color=discord.Color.red(),
                description="You're already marked as Looking For Team!",
            ).set_footer(text="Contact CORE if this is a mistake!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.selected_role = select.values[0]

        lookers_team = await teams.find_one(
            {
                "$or": [
                    {"players.discord_id": str(interaction.user.id)},
                    {"players.discord_id": interaction.user.name},
                ]
            }
        )

        if not lookers_team:
            embed = create_failure_embed(
                "You are not registered! Please [register](https://somnium.ccstiet.com/) to look for a team! If you are registered, please contact CORE",
                title="User not registered",
            )
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            return

        if len(lookers_team["players"]) > 1:
            # This used to fall through and respond a second time.
            embed = create_failure_embed("You need to run solo to join other teams!")
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            return

        # Create embed
        embed = create_success_embed(
            f"{interaction.user.mention} is looking for a team as `{self.selected_role.capitalize()}`",
            title="Player Looking for Team",
        )

        # Add Accept Button
        accept_button = discord.ui.Button(
            label="Invite to Team", style=discord.ButtonStyle.success
        )

        async def accept_callback(btn_interaction: discord.Interaction):
            if btn_interaction.user.id == self.player_id:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description="You can't invite yourself to your own team!",
                )

                await btn_interaction.response.send_message(
                    embed=embed, ephemeral=True, delete_after=3
                )

                return

            # Find the inviter's team
            inviter_team = await teams.find_one(
                {
                    "$or": [
                        {"players.discord_id": str(btn_interaction.user.id)},
                        {"players.discord_id": btn_interaction.user.name},
                    ]
                }
            )

            if not inviter_team:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    title="Team not found!",
                    description="You are not part of any team! If you are, please contact CORE",
                )

                await btn_interaction.response.send_message(
                    embed=embed, ephemeral=True, delete_after=10
                )
                return

            if inviter_team["team_name"] == lookers_team["team_name"]:
                await btn_interaction.response.send_message(
                    embed=create_failure_embed("You are both already on the same team."),
                    ephemeral=True,
                    delete_after=10,
                )
                return

            # Re-read the looker's team: somebody else may have grabbed them
            # while this message was sitting in the channel.
            current = await teams.find_one({"team_name": lookers_team["team_name"]})
            if current is None:
                await btn_interaction.response.send_message(
                    embed=create_failure_embed("This player has already joined a team."),
                    ephemeral=True,
                    delete_after=10,
                )
                return

            # Count current roles
            player_count = len(inviter_team["players"])
            hacker_count = sum(1 for p in inviter_team["players"] if p.get("is_hacker"))
            wizard_count = sum(1 for p in inviter_team["players"] if p.get("is_wizard"))

            # Do not allow more than 4 players
            if player_count >= MAX_TEAM_SIZE:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description=f"Your team already has {MAX_TEAM_SIZE} players!",
                )
                await btn_interaction.response.send_message(embed=embed, ephemeral=True)

                return

            # Role to add
            new_player_role = self.selected_role
            if new_player_role == "hacker" and hacker_count >= 2:
                await btn_interaction.response.send_message(
                    embed=create_failure_embed("Your team already has 2 hackers."),
                    ephemeral=True,
                )
                return

            if new_player_role == "wizard" and wizard_count >= 2:
                await btn_interaction.response.send_message(
                    embed=create_failure_embed("Your team already has 2 wizards."),
                    ephemeral=True,
                )
                return

            # Add first, remove second. The other order loses the player outright
            # if the write fails.
            result = await teams.update_one(
                {"team_name": inviter_team["team_name"]},
                {"$push": {"players": {"$each": current["players"]}}},
            )

            if not result.get("modified_count"):
                await btn_interaction.response.send_message(
                    embed=create_failure_embed(
                        "Could not move the player over. Please contact CORE."
                    ),
                    ephemeral=True,
                )
                return

            await teams.delete_one({"team_name": current["team_name"]})
            await _unmark_lft(self.player_id)

            await btn_interaction.response.send_message(
                embed=create_success_embed(
                    f"{interaction.user.mention} has been added to the team by {btn_interaction.user.mention}!"
                ),
                ephemeral=False,
            )

        accept_button.callback = accept_callback

        # Send embed with button
        view = discord.ui.View()
        view.add_item(accept_button)
        await interaction.channel.send(embed=embed, view=view)

        # Mark before confirming, so a failed write cannot leave the player
        # advertised but unmarked.
        await _mark_lft(interaction.user.id)

        await interaction.response.send_message(
            embed=create_success_embed(
                f"You've been marked as LFT as a {self.selected_role.capitalize()}!"
            ),
            ephemeral=True,
        )
