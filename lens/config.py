"""Local configuration. Secrets never enter templates or API responses."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
                name, value = raw.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


load_env()
LOCAL = ROOT / ".local"
DATABASE = LOCAL / "transcripts.sqlite3"
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GENERATION_MODEL = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.6-flash")
DIMENSIONS = 768
CHUNK_VERSION = "sentence-turns-v2-1200"
EMBEDDING_KEY = f"{EMBEDDING_MODEL}:{DIMENSIONS}:{CHUNK_VERSION}"


def api_key():
    return os.getenv("GEMINI_API_KEY", "").strip()
