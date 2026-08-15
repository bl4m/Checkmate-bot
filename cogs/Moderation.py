from logging import getLogger

import re
from discord.ext import commands
import discord

logger = getLogger(__name__)

censored = [
  "aand",
  "aandu",
  "balatkar",
  "beti chod",
  "bhenchod",
  "bhadva",
  "bhadve",
  "bua choddd",
  "bc",
  "bhandve",
  "bhootni ke",
  "bhosad",
  "bhosadi ke",
  "boobe",
  "chakke",
  "chinaal",
  "chinki",
  "chod",
  "chodu",
  "chodu bhagat",
  "chooche",
  "choochi",
  "choot",
  "choot ke baal",
  "chootia",
  "chootiya",
  "chuche",
  "chuchi",
  "chudai khanaa",
  "chudan chudai",
  "chut",
  "chut ke baal",
  "chut ke dhakkan",
  "chut maarli",
  "chutad",
  "chutadd",
  "chutan",
  "chutia",
  "chutiya",
  "gaand",
  "gaandfat",
  "gaandmasti",
  "gaandufad",
  "gandu",
  "gashti",
  "gasti",
  "ghassa",
  "ghasti",
  "harami",
  "haramzade",
  "hawas",
  "hawas ke pujari",
  "hijda",
  "hijra",
  "jhant",
  "jhant chaatu",
  "jhant ke baal",
  "jhantu",
  "kamine",
  "kaminey",
  "kanjar",
  "kutta",
  "kutta kamina",
  "kutte ki aulad",
  "kutte ki jat",
  "kuttiya",
  "loda",
  "lodu",
  "lund",
  "lund choos",
  "lund khajoor",
  "lundtopi",
  "lundure",
  "maa ki chut",
  "maal",
  "madar chod",
  "mooh mein le",
  "mutth",
  "najayaz",
  "najayaz aulaad",
  "najayaz paidaish",
  "pakistan",
  "pataka",
  "patakha",
  "raand",
  "randi",
  "saala",
  "saala kutta",
  "saali kutti",
  "saali randi",
  "suar",
  "suar ki aulad",
  "tatte",
  "tatti",
  "teri maa ka bhosada",
  "teri maa ka boba chusu",
  "teri maa ki chut",
  "tharak",
  "tharki",
]

# Set to True to let admins / anyone with Manage Messages past the filter.
EXEMPT_MODERATORS = False

LEET = {
    '@': 'a', '4': 'a',
    '1': 'i', '!': 'i', '|': 'i',
    '$': 's', '5': 's',
    '0': 'o'
}


def normalize(text:str) -> str:
    text = text.lower()

    for symbol, letter in LEET.items():
        text = text.replace(symbol, letter)

    text = re.sub(r"[^\w\s]", "", text)
    return text


def strip_punctuation(text: str) -> str:
    """Punctuation removed but no leet folding."""
    return re.sub(r"[^\w\s]", "", text.lower())


def candidates(text: str) -> tuple[str, str]:
    """Both readings of a message.

    Folding leet first turns trailing '!' into 'i', so "bhenchod!!" became
    "bhenchodii" and slipped through. Checking the un-folded text as well
    catches that without giving up on "b!tch" style evasion.
    """
    return normalize(text), strip_punctuation(text)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # re.escape each term so a stray metacharacter in the list cannot turn
        # into a wildcard that matches far more than intended.
        pattern = "|".join(re.escape(word) for word in censored)
        self.profanity_regex = re.compile(rf"\b({pattern})\b", re.IGNORECASE)

    def _is_exempt(self, message: discord.Message) -> bool:
        if not EXEMPT_MODERATORS:
            return False
        author = message.author
        if not isinstance(author, discord.Member):
            return False
        perms = author.guild_permissions
        return perms.administrator or perms.manage_messages

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # The bot cannot delete somebody else's DM, so filtering there only ever
        # produced a Forbidden error.
        if message.guild is None:
            return

        if self._is_exempt(message):
            return

        match = None
        for cleaned_content in candidates(message.content):
            match = self.profanity_regex.search(cleaned_content)
            if match:
                break

        if not match:
            return

        try:
            await message.delete()
            logger.info(
                "Deleted message from %s (%s) in #%s, matched %r",
                message.author,
                message.author.id,
                message.channel,
                match.group(0),
            )
            await message.channel.send(
                f"{message.author.mention}, that word isn't allowed here!",
                delete_after=5,
            )
        except discord.Forbidden:
            logger.warning("Missing permissions to delete messages or send alerts.")
        except discord.HTTPException as e:
            logger.error(f"Failed to delete message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
