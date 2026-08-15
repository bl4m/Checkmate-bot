from logging import getLogger
from os import getenv

import discord
from aiohttp import ClientSession, ClientError
from discord.ext import commands

logger = getLogger(__name__)


def _channel_id() -> int | None:
    raw = getenv("ANNOUNCEMENT_CHANNEL")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.error("ANNOUNCEMENT_CHANNEL is not a valid channel id: %r", raw)
        return None


class Broadcast(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # int(None) used to raise here and take the whole cog down silently.
        self.announcement_channel = _channel_id()
        self.post_url = getenv("BROADCAST_URI")

        if self.announcement_channel is None:
            logger.warning("ANNOUNCEMENT_CHANNEL unset; broadcasting is disabled.")
        if not self.post_url:
            logger.warning("BROADCAST_URI unset; broadcasting is disabled.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.announcement_channel is None or not self.post_url:
            return

        if message.channel.id != self.announcement_channel or message.author.bot:
            return

        data = {
            "author": message.author.name,
            "content": message.content,
            "timestamp": str(message.created_at),
        }

        async with ClientSession() as session:
            try:
                async with session.post(self.post_url, json=data) as resp:
                    if resp.status != 200:
                        logger.error(f"POST failed: {resp.status}")
            except (ClientError, OSError) as e:
                logger.error(f"Error posting message: {e}")

        # No process_commands() here: Bot.on_message already runs it, and calling
        # it again from a listener made every prefix command in this channel fire
        # twice.


async def setup(bot: commands.Bot):
    await bot.add_cog(Broadcast(bot))
