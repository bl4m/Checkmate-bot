from logging import getLogger

import aiosqlite
import discord

from database import teams
from views.utils import create_failure_embed, create_success_embed

logger = getLogger(__name__)
assert teams is not None, "Teams collection is None!"


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
        async with aiosqlite.connect("lft.db") as db:
            cursor = await db.execute(
                "SELECT 1 FROM lft_users WHERE discord_id = ?", (interaction.user.id,)
            )
            exists = await cursor.fetchone()

            if exists:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description="You're already marked as Looking For Team!",
                ).set_footer(text="Contact CORE if this is a mistake!")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        if not isinstance(interaction.channel, discord.TextChannel):
            return

        if interaction.user.id != self.player_id:
            embed = create_failure_embed("This isn't your LFT panel.")
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
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
                "You are not registered! Please [register](https://obscura.ccstiet.com/) to look for a team! If you are registered, please contact CORE",
                title="User not registered",
            )
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            return

        if len(lookers_team["players"]) > 1:
            embed = create_failure_embed("You need to run solo to join other teams!")
            await interaction.response.send_message(
                embed=embed, ephemeral=True, delete_after=10
            )
            await interaction.delete_original_response()

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

            # Count current roles
            player_count = sum(1 for p in inviter_team["players"])
            hacker_count = sum(1 for p in inviter_team["players"] if p.get("is_hacker"))
            wizard_count = sum(1 for p in inviter_team["players"] if p.get("is_wizard"))

            # Do not allow more than 4 players
            if player_count >= 4:
                embed = discord.Embed(
                    color=discord.Color.red(),
                    description="Your team already has 2 hackers!",
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

            await teams.update_one(
                {"_id": inviter_team["_id"]},
                {"$push": {"players": {"$each": lookers_team["players"]}}},
            )

            await teams.delete_one({"_id": lookers_team["_id"]})

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

        await interaction.response.send_message(
            embed=create_success_embed(
                f"You've been marked as LFT as a {self.selected_role.capitalize()}!"
            ),
            ephemeral=True,
        )

        await db.execute(
            "INSERT INTO lft_users (discord_id) VALUES (?)", (interaction.user.id,)
        )
        await db.commit()

        await interaction.delete_original_response()
