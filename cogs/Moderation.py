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
  "bhadva",
  "bhadve",
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
  "paki",
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

def normalize(text:str) -> str:
    text = text.lower()

    replacements = {
        '@': 'a', '4': 'a',
        '1': 'i', '!': 'i', '|': 'i',
        '$': 's', '5': 's',
        '0': 'o'
    }
    for symbol, letter in replacements.items():
        text = text.replace(symbol, letter)

    text = re.sub(r"[^\w\s]", "", text)
    return text

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profanity_regex = re.compile(rf"\b({'|'.join(censored)})\b", re.IGNORECASE)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.author.bot or not self.profanity_regex:
            return

        cleaned_content = normalize(message.content)

        if self.profanity_regex.search(cleaned_content):
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, that word isn't allowed here!", delete_after=5)
            except discord.Forbidden:
                print("Missing permissions to delete messages or send alerts.")
            except discord.HTTPException as e:
                print(f"Failed to delete message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
