from logging import getLogger
from typing import Any

import aiosqlite
import discord
import loggers  # Ensure logging config is initialized before any loggers are used.
from discord import app_commands
from discord.ext import commands

import database  # Initializing database
from settings import LFT_DB_PATH
from utils import COGS, DISCORD_API_TOKEN

logger = getLogger(__name__)


class Bot(commands.Bot):
    def __init__(
        self,
        command_prefix,
        *,
        help_command: commands.HelpCommand | None = None,
        tree_cls: type[app_commands.CommandTree[Any]] = app_commands.CommandTree,
        description: str | None = None,
        intents: discord.Intents,
        **options: Any,
    ) -> None:
        super().__init__(
            command_prefix,
            help_command=help_command,
            tree_cls=tree_cls,
            description=description,
            intents=intents,
            **options,
        )
        self.initial_extensions = COGS

    # Lazy Loads every cog in the cogs directory
    async def setup_hook(self):
        await database.init_db()
        await setup_lft_db()

        # Register the persistent view exactly once. Doing this in on_ready meant
        # re-registering it on every reconnect.
        from views.TeamChannel import TeamChannelButton

        self.add_view(TeamChannelButton())

        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Successfully loaded {extension}!")
            except Exception as e:
                logger.error(f"Error loading extension {extension}: {e}")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")

        except Exception as e:
            logger.error(e)

    async def on_ready(self):
        logger.info("Bot is Up and ready!")


async def setup_lft_db():
    async with aiosqlite.connect(LFT_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lft_users (
                discord_id INTEGER PRIMARY KEY
            )
        """)
        await db.commit()


def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True  # required to fetch member info
    intents.guilds = True

    bot = Bot(command_prefix="!", intents=intents, help_command=None)

    if not DISCORD_API_TOKEN:
        raise SystemExit("Missing Discord bot token! Set DISCORD_API_TOKEN in .env")

    bot.run(DISCORD_API_TOKEN)


if __name__ == "__main__":
    main()
