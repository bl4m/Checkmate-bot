from logging import getLogger

import discord
from discord.ext import commands

logger = getLogger(__name__)


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rules")
    async def rules(self, ctx: commands.Context):
        """
        Rules for Somnium Event
        """
        embed = discord.Embed(
            title="📒 Somnium Rules",
            description="Keep the experience fair, respectful, and focused on the game.",
            color=discord.Color.from_rgb(168, 85, 247),
        )
        embed.add_field(
            name="1. Be respectful",
            value="Treat everyone with kindness. Harassment, hate speech, and discrimination are not tolerated.",
            inline=False,
        )
        embed.add_field(
            name="2. Stay in the right channels",
            value="Use the appropriate channels for announcements, team coordination, and support. Avoid off-topic spam.",
            inline=False,
        )
        embed.add_field(
            name="3. Keep things safe and clean",
            value="No NSFW, offensive, or disruptive content. Respect the event atmosphere and the people in it.",
            inline=False,
        )
        embed.add_field(
            name="4. Play fair",
            value=(
                "• Work only through your own team's voice channel\n"
                "• Don't share puzzle answers outside your team\n"
                "• Follow organizer instructions closely"
            ),
            inline=False,
        )
        embed.add_field(
            name="5. Report problems early",
            value="If you see a violation or need help, contact the CCS team or CORE with evidence when needed.",
            inline=False,
        )
        embed.set_footer(text="Somnium • Communication and teamwork are the key to success")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="links")
    async def links(self, ctx: commands.Context):
        """
        Important Links
        """
        embed = discord.Embed(
            title="🔗 Important Links",
            description="Everything you need for Somnium, in one place.",
            color=discord.Color.from_rgb(59, 130, 246),
        )
        embed.add_field(
            name="🌐 Somnium Portal",
            value="[somnium.ccstiet.com](https://somnium.ccstiet.com) — registration, team dashboard, and event updates",
            inline=False,
        )
        embed.add_field(
            name="📸 CCS on Instagram",
            value="[@ccs_tiet](https://www.instagram.com/ccs_tiet/) — announcements and highlights",
            inline=False,
        )
        embed.set_footer(text="Somnium • Bookmark the portal — your team dashboard lives there")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
