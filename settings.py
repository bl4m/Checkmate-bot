from os import getenv

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int | None = None) -> int | None:
    value = getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


EVENT_NAME = "Somnium"
CATEGORY_NAME = getenv("VOICE_CATEGORY_NAME", "SOMNIUM VOICE CHANNELS")
CATEGORY_FALLBACK = getenv("CATEGORY_FALLBACK_NAME", "SOMNIUM")
TEAM_CHANNEL = getenv("TEAM_CHANNEL")
ANNOUNCEMENT_CHANNEL = getenv("ANNOUNCEMENT_CHANNEL")
ADMIN_ROLE = getenv("ADMIN_ROLE")
JOIN_CHANNEL_ID = _get_int("JOIN_CHANNEL_ID", 1395877470590341290)
ABOUT_CHANNEL_ID = _get_int("ABOUT_CHANNEL_ID", 1395877004368281620)
RULES_CHANNEL_ID = _get_int("RULES_CHANNEL_ID", 1395877379175485701)
JOIN_CHANNEL_NAME = getenv("JOIN_CHANNEL_NAME", "🚀・join-team-channel")
ABOUT_CHANNEL_NAME = getenv("ABOUT_CHANNEL_NAME", "🔎・about")
RULES_CHANNEL_NAME = getenv("RULES_CHANNEL_NAME", "📜・rules")
