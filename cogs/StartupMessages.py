import asyncio
from logging import getLogger
from os import path

import discord
from discord.ext import commands

from settings import (
    ABOUT_CHANNEL_ID,
    ABOUT_CHANNEL_NAME,
    CATEGORY_FALLBACK,
    EVENT_NAME,
    JOIN_CHANNEL_ID,
    JOIN_CHANNEL_NAME,
    RULES_CHANNEL_ID,
    RULES_CHANNEL_NAME,
)
from views import TeamChannelButton

logger = getLogger(__name__)
CATEGORY_NAME = CATEGORY_FALLBACK

BANNER_PATH = path.join("assets", "banner.png")
LOGO_PATH = path.join("assets", "logo.png")


# A discord.File closes its handle once sent, so every send needs a fresh one.
def _banner() -> discord.File:
    return discord.File(BANNER_PATH, filename="banner.png")


def _logo() -> discord.File:
    return discord.File(LOGO_PATH, filename="logo.png")


class StartupMessages(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.join_channel_id = JOIN_CHANNEL_ID
        self.about_channel_id = ABOUT_CHANNEL_ID
        self.rules_channel_id = RULES_CHANNEL_ID

    @commands.hybrid_command(name="setup-somnium-channels")
    @commands.has_permissions(administrator=True)
    async def setup_somnium_channels(self, ctx: commands.Context):
        """Create the Somnium channels and post the startup messages when needed."""
        if not ctx.guild:
            return

        await ctx.defer(ephemeral=True)

        try:
            await asyncio.gather(
                self.send_about_event_message(),
                self.send_join_team_event_message(),
                self.send_rules_event_message(),
            )
            await ctx.send("Somnium setup channels and welcome messages are ready.", ephemeral=True)
        except Exception:
            logger.exception("Error in setup_somnium_channels")
            await ctx.send("Failed to set up Somnium channels.", ephemeral=True)

    async def _validate(
        self, channel_id: int | None, channel_name: str
    ) -> discord.TextChannel | None:
        guild = self.bot.guilds[0] if self.bot.guilds else None

        if not guild:
            logger.warning("Guild not found. Aborting message sending task.")
            return None

        channel = self.bot.get_channel(channel_id) if channel_id is not None else None
        if channel is None:
            channel = discord.utils.get(guild.text_channels, name=channel_name)

        if channel is None:
            category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
            try:
                channel = await guild.create_text_channel(channel_name, category=category)
            except discord.HTTPException:
                logger.exception("Failed to create startup channel %s", channel_name)
                return None

        if not isinstance(channel, discord.TextChannel):
            logger.error("Channel must be a Text Channel!")
            return None

        return channel

    async def send_join_team_event_message(self):
        logger.info("Sending event message")

        channel = await self._validate(self.join_channel_id, JOIN_CHANNEL_NAME)

        if channel is None:
            return

        self.join_channel_id = channel.id

        if channel.last_message_id:
            logger.info("Join channel already initialized; skipping duplicate send.")
            return

        embed = discord.Embed(
            title=f"Welcome to {EVENT_NAME}!",
            description=(
                "Your team is waiting for you inside the dream.\n\n"
                "Click the button below to join your team’s voice channel and get started."
            ),
            color=discord.Color.from_rgb(153, 102, 255),
        )
        embed.add_field(
            name="Before you begin",
            value=(
                "• Make sure your Discord username matches the one submitted during registration\n"
                "• Use the event channels only for Somnium-related discussion\n"
                "• Reach out to Core if you run into any issue"
            ),
            inline=False,
        )
        embed.add_field(
            name="Your goal",
            value="Join your team, settle into the voice channel, and begin the event together.",
            inline=False,
        )
        embed.set_thumbnail(url="attachment://logo.png")
        embed.set_footer(text="Somnium • Team coordination starts here")

        await channel.send(embed=embed, view=TeamChannelButton(), file=_logo())

    async def send_about_event_message(self):
        logger.info("Sending about messsage")

        channel = await self._validate(self.about_channel_id, ABOUT_CHANNEL_NAME)

        if channel is None:
            return

        self.about_channel_id = channel.id

        messages = [m async for m in channel.history(limit=1)]
        if messages:
            logger.info("Channel already sent before! for about")
            return

        embed = discord.Embed(
            title=f"About {EVENT_NAME}",
            description=(
                f"[Somnium](https://somnium.ccstiet.com/) is a team-based escape experience set inside a shared dream world.\n\n"
                "Your squad must navigate four memories from the past, each packed with puzzles, pressure, and a path to reality."
            ),
            color=discord.Color.from_rgb(59, 130, 246),
        )
        embed.add_field(
            name="What to expect",
            value=(
                "• Team-based progression\n"
                "• Puzzle-driven challenges\n"
                "• Shared decision-making under pressure\n"
                "• A story that unfolds across each memory"
            ),
            inline=False,
        )
        embed.add_field(
            name="The question",
            value="Will your team wake up together, or remain lost in the dreamscape forever?",
            inline=False,
        )
        embed.set_image(url="attachment://banner.png")

        await channel.send(embed=embed, file=_banner())

    async def send_rules_event_message(self):
        logger.info("sending rules message")

        channel = await self._validate(self.rules_channel_id, RULES_CHANNEL_NAME)

        if channel is None:
            return

        self.rules_channel_id = channel.id

        messages = [m async for m in channel.history(limit=1)]
        if messages:
            logger.info("Channel already sent before! rules")
            return
        embed = discord.Embed(
            title="📒 General Rules",
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
            name="4. Report problems early",
            value="If you see a violation or need help, contact the CCS team or Core with evidence when needed.",
            inline=False,
        )

        embed1 = discord.Embed(
            title="📘 Team Rules",
            description="The event runs best when teams stay organised and communicate clearly.",
            color=discord.Color.from_rgb(34, 197, 94),
        )
        embed1.add_field(
            name="Team flow",
            value=(
                "• Join using the correct Discord username or ID\n"
                "• Work together through your assigned team voice channel\n"
                "• Keep all event discussion in the proper channels\n"
                "• Follow organizer instructions closely"
            ),
            inline=False,
        )
        embed1.set_footer(text="Communication and teamwork are the key to success.")

        embed.set_thumbnail(url="attachment://logo.png")

        await channel.send(embeds=[embed, embed1], file=_logo())


async def setup(bot: commands.Bot):
    await bot.add_cog(StartupMessages(bot))
