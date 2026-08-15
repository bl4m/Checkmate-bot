"""Shared helpers for team roles, categories and voice channels.

Both the ``/click here`` button (views/TeamChannel.py) and the member-join
listener (cogs/TeamChannel.py) used to carry their own copy of this logic, and
the two copies had drifted apart. Keep it here so they cannot drift again.
"""

import random
from logging import getLogger

import discord

from settings import CATEGORY_NAME

logger = getLogger(__name__)

# Discord refuses more than 50 channels in a single category.
MAX_CHANNELS_PER_CATEGORY = 50

ROLE_COLORS = [
    discord.Color.red(),
    discord.Color.blue(),
    discord.Color.green(),
    discord.Color.gold(),
    discord.Color.purple(),
    discord.Color.orange(),
    discord.Color.teal(),
    discord.Color.magenta(),
]

TEAM_ACCESS = discord.PermissionOverwrite(view_channel=True, connect=True)
NO_ACCESS = discord.PermissionOverwrite(view_channel=False, connect=False)


def normalize_team_name(team_name: str) -> str:
    """Team name as it appears in channel names: 'Red Raptors' -> 'red-raptors'."""
    return team_name.strip().lower().replace(" ", "-")


def team_role_name(team_name: str) -> str:
    return f"team-{normalize_team_name(team_name)}"


async def get_or_create_team_role(
    guild: discord.Guild, team_name: str
) -> discord.Role | None:
    """Return the team's role, creating it the first time we see the team."""
    role_name = team_role_name(team_name)
    role = discord.utils.get(guild.roles, name=role_name)
    if role is not None:
        return role

    try:
        return await guild.create_role(
            name=role_name,
            color=random.choice(ROLE_COLORS),
            reason=f"Role for {team_name} team",
            mentionable=True,
        )
    except discord.HTTPException:
        logger.exception("Could not create role %s", role_name)
        return None


async def _get_or_create_category(guild: discord.Guild) -> discord.CategoryChannel | None:
    """Find a team category with room left, or open the next one.

    Every category we create must start with CATEGORY_NAME, otherwise this
    lookup (and the cleanup command) will never find it again.
    """
    for category in guild.categories:
        if (
            category.name.startswith(CATEGORY_NAME)
            and len(category.voice_channels) < MAX_CHANNELS_PER_CATEGORY
        ):
            return category

    existing = sum(1 for c in guild.categories if c.name.startswith(CATEGORY_NAME))
    name = CATEGORY_NAME if existing == 0 else f"{CATEGORY_NAME} #{existing + 1}"

    try:
        return await guild.create_category(
            name=name, overwrites={guild.default_role: NO_ACCESS}
        )
    except discord.HTTPException:
        logger.exception("Could not create category %s", name)
        return None


async def ensure_team_voice_channel(
    guild: discord.Guild,
    team_name: str,
    members: list[discord.Member],
    role: discord.Role | None = None,
    *,
    prune: bool = False,
) -> discord.VoiceChannel | None:
    """Create the team's voice channel, or grant `members` access to it.

    `prune=True` also strips member overwrites that are no longer on the team.
    Only pass it when `members` is the *complete* roster, never when you are
    adding a single person.
    """
    normalized = normalize_team_name(team_name)

    overwrites: dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite] = {
        guild.default_role: NO_ACCESS,
    }
    if role is not None:
        overwrites[role] = TEAM_ACCESS
    for member in members:
        overwrites[member] = TEAM_ACCESS

    channel = discord.utils.get(guild.voice_channels, name=normalized)

    if channel is not None:
        try:
            if role is not None and channel.overwrites_for(role) != TEAM_ACCESS:
                await channel.set_permissions(role, overwrite=TEAM_ACCESS)

            for member in members:
                if channel.overwrites_for(member) != TEAM_ACCESS:
                    await channel.set_permissions(member, overwrite=TEAM_ACCESS)

            if prune:
                for target in list(channel.overwrites):
                    if isinstance(target, discord.Member) and target not in members:
                        await channel.set_permissions(target, overwrite=None)
        except discord.HTTPException:
            logger.exception("Could not update permissions on %s", normalized)
        return channel

    category = await _get_or_create_category(guild)
    if category is None:
        return None

    try:
        return await guild.create_voice_channel(
            name=normalized, category=category, overwrites=overwrites
        )
    except discord.HTTPException:
        logger.exception("Could not create voice channel %s", normalized)
        return None
