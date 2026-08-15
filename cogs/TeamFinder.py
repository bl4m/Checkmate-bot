from logging import getLogger

from discord.ext import commands

from settings import TEAM_CHANNEL
from views import LookingForTeamView
from views.utils import create_failure_embed

logger = getLogger(__name__)


class TeamFinder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command("team-finder")
    async def lft(self, ctx: commands.Context):
        # The channel id used to be hardcoded here while TEAM_CHANNEL sat unused
        # in .env. TEAM_CHANNEL is now the single source of truth.
        if TEAM_CHANNEL is not None and ctx.channel.id != TEAM_CHANNEL:
            embed = create_failure_embed(
                "You can only run this command in the find-teammates channel!",
                title="Permission Denied",
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        view = LookingForTeamView(ctx.author.id)
        await ctx.send("Select your role:", view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TeamFinder(bot))
