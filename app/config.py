import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
GRAPH_API_BASE = os.getenv("GRAPH_API_BASE", "https://graph.instagram.com/v21.0")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

DRY_RUN = _bool("DRY_RUN", "true")
REPLY_TO_DMS = _bool("REPLY_TO_DMS", "true")
REPLY_TO_COMMENTS = _bool("REPLY_TO_COMMENTS", "true")
MAX_REPLIES_PER_USER_PER_HOUR = int(os.getenv("MAX_REPLIES_PER_USER_PER_HOUR", "10"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

DB_PATH = os.getenv("DB_PATH", str(ROOT / "bot.db"))
VOICE_PATH = Path(os.getenv("VOICE_PATH", str(ROOT / "config" / "voice.md")))
KEYWORDS_PATH = Path(os.getenv("KEYWORDS_PATH", str(ROOT / "config" / "keywords.json")))
