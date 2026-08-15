import random

import discord
from discord.ext import commands, tasks


class StatusRotator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_messages = [
            "Create new teams",
            "Solving CTF Questions",
            "Looking for messages",
            "Listening for registrations",
            "Matchmaking players",
            "Getting lost in the maze",
        ]
        self.rotate_status.start()

    @tasks.loop(minutes=1)
    async def rotate_status(self):
        status = random.choice(self.status_messages)
        await self.bot.change_presence(
            activity=discord.Game(name=status),
            status=discord.Status.online,
        )

    @rotate_status.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusRotator(bot))
