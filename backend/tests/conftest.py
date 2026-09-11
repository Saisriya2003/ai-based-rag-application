"""Test configuration: isolated SQLite file, offline modes forced.

Environment is fixed *before* ``app.config`` is imported anywhere, so the test
run never touches ``backend/data/lumen.db``, a developer's Postgres, or OpenAI.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="lumen-tests-"))
os.environ["SQLITE_PATH"] = str(_TMP / "lumen-test.db")
os.environ["DATABASE_URL"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["SENTENCE_TRANSFORMERS"] = "0"
