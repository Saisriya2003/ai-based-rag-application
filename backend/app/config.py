"""Environment and runtime settings. Loads a nearby .env if present."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / ".env",
        here.parents[1] / ".env",
        Path.cwd() / ".env",
    ]
    seen: set[Path] = set()
    for path in candidates:
        path = path.resolve()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


def _clean(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


DATABASE_URL = _clean("DATABASE_URL")
OPENAI_API_KEY = _clean("OPENAI_API_KEY")
OPENAI_MODEL = _clean("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"
SENTENCE_TRANSFORMERS = _clean("SENTENCE_TRANSFORMERS") in {"1", "true", "True", "yes"}

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
# Optional override for the SQLite file (used by the test suite and handy for
# running several isolated libraries side by side).
SQLITE_PATH = Path(_clean("SQLITE_PATH")) if _clean("SQLITE_PATH") else DATA_DIR / "rag.db"


def database_kind() -> str:
    return "postgresql" if DATABASE_URL else "sqlite"


def generation_mode() -> str:
    return "llm" if OPENAI_API_KEY else "extractive"


def embedding_backend() -> str:
    return "sentence-transformers" if SENTENCE_TRANSFORMERS else "hashing"
