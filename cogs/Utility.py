from logging import getLogger
from discord.ext import commands
from discord.embeds import Embed
import discord
from views.utils import create_success_embed

logger = getLogger(__name__)

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rules")
    
    async def rules(self, ctx: commands.Context):
        """
        Rules for Somnium Event
        """
        await ctx.send(embed=create_success_embed("rules message", "Rules"))

    @commands.hybrid_command(name="links")
    async def links(self, ctx: commands.Context): 
        """
            Important Links
        """
        await ctx.send(embed=create_success_embed("[Somnium](https://somnium.ccstiet.com)\n[CCS](https://www.instagram.com/ccs_tiet/)", "Links"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
