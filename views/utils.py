import discord


def create_success_embed(message: str, title: str | None = None):
    embed = discord.Embed(color=discord.Color.green(), description=message, title=title)
    return embed


def create_failure_embed(message: str, title: str | None = None):
    embed = discord.Embed(color=discord.Color.red(), description=message, title=title)
    return embed
