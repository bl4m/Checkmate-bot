from logging import getLogger

from discord.ext import commands

from views import LookingForTeamView
from views.utils import create_failure_embed
from settings import TEAM_CHANNEL,ADMIN_ROLE


logger = getLogger(__name__)

class TeamFinder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command("team-finder")
    async def lft(self, ctx: commands.Context):
        print(ctx.channel.id)
        if ctx.channel.id != 1537917791468912730:
            embed = create_failure_embed(
                "You can only run this command in 🤝・find-teammates-here!",
                title="Permission Denied",
            )
            await ctx.send(embed=embed)
            return

        view = LookingForTeamView(ctx.author.id)
        await ctx.send("Select your role:", view=view, ephemeral=True)

    # @commands.hybrid_command("set-teamfinder")
    # @commands.has_role(ADMIN_ROLE)
    # def stf(self, ctx:commands.Context):



async def setup(bot: commands.Bot):
    await bot.add_cog(TeamFinder(bot))
