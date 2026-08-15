from os import getenv, listdir

from dotenv import load_dotenv

load_dotenv()


def get_cogs(path: str, prefix: str):
    # These two load cleanly now, but they mutate team rows (AutoPairing merges
    # and deletes teams; TeamFinder moves a player between teams) and the
    # hacker/wizard counts they rely on are not stored in the Somnium table yet.
    # Delete a name from this set to put the feature live.
    excluded = {"AutoParing.py", "TeamFinder.py"}
    files = listdir(path)
    return [
        f"{prefix}.{f[:-3]}"
        for f in files
        if f.endswith(".py") and f != "__init__.py" and f not in excluded
    ]


COGS = get_cogs("cogs", "cogs")
DISCORD_API_TOKEN = getenv("DISCORD_API_TOKEN")
