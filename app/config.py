from __future__ import annotations

import json
import os
from pathlib import Path


APP_NAME = "Amadda"
APP_VERSION = "0.1.0"
BASE_DIR = Path(__file__).resolve().parent.parent

# exe(frozen) 환경이면 데이터를 %APPDATA%\Amadda\ 에 저장
# 개발 환경이면 프로젝트 루트 data/ 에 저장
import sys as _sys
DATA_DIR = (
    Path(os.environ.get("APPDATA", Path.home())) / "Amadda"
    if getattr(_sys, "frozen", False)
    else BASE_DIR / "data"
)
DB_PATH = DATA_DIR / "amadda.db"
API_HOST = "127.0.0.1"
API_PORT = 8765
SNAPSHOT_RETENTION_MAX = 288
AUTO_SNAPSHOT_INTERVAL_MINUTES = 15

# 설정 파일: %APPDATA%\Amadda\settings.json
# exe로 배포 시에도 유지되는 위치
SETTINGS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Amadda"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"


def _load_settings() -> dict:
    try:
        if SETTINGS_PATH.exists():
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_settings(patch: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    current = _load_settings()
    current.update(patch)
    SETTINGS_PATH.write_text(
        json.dumps(current, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_setting(key: str, default=None):
    return _load_settings().get(key, default)


# 환경변수 우선 → settings.json → 빈 문자열
GEMINI_API_KEY: str = (
    os.environ.get("GEMINI_API_KEY")
    or get_setting("gemini_api_key")
    or ""
)
