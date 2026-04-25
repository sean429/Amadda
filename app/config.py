from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "Amadda"
APP_VERSION = "0.1.0"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "amadda.db"
API_HOST = "127.0.0.1"
API_PORT = 8765
SNAPSHOT_RETENTION_MAX = 288
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
