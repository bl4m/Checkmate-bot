from logging import getLogger

import discord
from discord.ext import commands

from database import teams

from .utils import create_failure_embed

logger = getLogger(__name__)


class ConfirmView(discord.ui.View):
    def __init__(self, bot: commands.Bot, pairs: list[tuple], interaction_user_id: int):
        super().__init__(timeout=60)
        self.bot = bot
        self.pairs = pairs
        self.interaction_user_id = interaction_user_id
        self.confirmed = False

    def disable_all_items(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.red)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.interaction_user_id:
            embed = create_failure_embed(
                "You're not allowed to confirm this.", title="Permission Denied"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer()

        merged = 0

        for a, b in self.pairs:
            players = a["players"] + b["players"]

            # Sequential and checked: running these concurrently meant a failed
            # merge could still be followed by the delete, dropping a whole team.
            result = await teams.update_one(
                {"team_name": a["team_name"]}, {"$set": {"players": players}}
            )

            if not result.get("modified_count"):
                logger.error(
                    "Could not merge %s into %s; leaving both teams untouched.",
                    b["team_name"],
                    a["team_name"],
                )
                continue

            await teams.delete_one({"team_name": b["team_name"]})
            merged += 1

        self.confirmed = True
        self.disable_all_items()
        await interaction.edit_original_response(
            content=f"✅ {merged}/{len(self.pairs)} pairs confirmed and saved to DB.",
            view=self,
        )
