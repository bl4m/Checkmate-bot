import asyncio
from logging import getLogger
from os import getenv

import discord
from discord.ext import commands

from database import teams
from views import ConfirmView

logger = getLogger(__name__)
ADMIN_ROLE = getenv("ADMIN_ROLE")

assert teams is not None, "Teams collection is None!"
assert ADMIN_ROLE is not None, "Admin role not found!"


class AutoPairing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = teams

    # Its been a long time since i used my brain like this
    def pair_teams_linear(self, teams_iterable):
        size_buckets = {1: [], 2: [], 3: []}
        for team in teams_iterable:
            n = len(team["players"])
            if 1 <= n <= 3:
                size_buckets[n].append(team)

        result = []

        # Pair 2 + 2
        twos = size_buckets[2]
        while len(twos) >= 2:
            result.append((twos.pop(), twos.pop()))

        # Pair 3 + 1
        ones, threes = size_buckets[1], size_buckets[3]
        while ones and threes:
            result.append((ones.pop(), threes.pop()))

        return result

    @commands.hybrid_command(description="Auto-pair teams so total players = 4")
    @commands.has_role(ADMIN_ROLE)
    async def autopair_bulk(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        teams = [t async for t in self.db.find({}).batch_size(200)]
        paired = await asyncio.to_thread(self.pair_teams_linear, teams)

        if not paired:
            return await ctx.send(
                "No valid pairs found.", ephemeral=not ctx.interaction
            )

        lines = [
            f"✅ `{a['team_name']}` ({len(a['players'])}) + `{b['team_name']}` ({len(b['players'])})"
            for a, b in paired
        ]
        description = "\n".join(lines)

        embed = discord.Embed(
            title="🧠 Auto-Paired Teams",
            description=description,
            color=discord.Color.green(),
        )

        view = ConfirmView(
            bot=self.bot, pairs=paired, interaction_user_id=ctx.author.id
        )

        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(AutoPairing(bot))
