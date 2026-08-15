from os import getenv, listdir

from dotenv import load_dotenv

load_dotenv()


def get_cogs(path: str, prefix: str):
    excluded = {"AutoParing.py", "TeamFinder.py"}
    files = listdir(path)
    return [
        f"{prefix}.{f[:-3]}"
        for f in files
        if f.endswith(".py") and f != "__init__.py" and f not in excluded
    ]


COGS = get_cogs("cogs", "cogs")
DISCORD_API_TOKEN = getenv("DISCORD_API_TOKEN")
