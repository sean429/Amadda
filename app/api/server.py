from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.models import CommandResponse, SnapshotItem, TrackedProcess
from app.services import auto_snapshot, dispatcher, parser, permission_service, repository, wake_word


logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "ui" / "frontend"


class CommandRequest(BaseModel):
    text: str
    confirmed: bool = False


class BrowserTabRequest(BaseModel):
    url: str
    title: str
    active: bool


class BrowserSnapshotRequest(BaseModel):
    browser: str = "chrome"
    tabs: list[BrowserTabRequest]


class TrackedProcessRequest(BaseModel):
    process_name: str
    executable_path: str | None = None
    window_title: str | None = None


def command_response_to_dict(response: CommandResponse) -> dict[str, Any]:
    return {
        "intent": {
            "intent": response.intent.intent,
            "params": response.intent.params,
            "requires_confirmation": response.intent.requires_confirmation,
            "raw_text": response.intent.raw_text,
        },
        "permission": {
            "requires_confirmation": response.permission.requires_confirmation,
            "reason": response.permission.reason,
        },
        "result": None
        if response.result is None
        else {
            "success": response.result.success,
            "message": response.result.message,
            "data": response.result.data,
        },
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Amadda Local API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Static frontend ---
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    # --- Health ---
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # --- Snapshots ---
    @app.get("/snapshots/latest")
    def latest_snapshot() -> dict[str, Any]:
        record = repository.get_latest_snapshot()
        if record is None:
            return {"snapshot": None}
        return {"snapshot": _snapshot_to_dict(record)}

    @app.get("/snapshots/history")
    def snapshot_history(n: int = 20) -> dict[str, Any]:
        records = repository.get_recent_snapshots(n=n)
        return {"snapshots": [_snapshot_to_dict(r) for r in records]}

    # --- Command ---
    @app.post("/command")
    def handle_command(request: CommandRequest) -> dict[str, Any]:
        intent = parser.parse(request.text)
        permission = permission_service.evaluate(intent)
        result = None
        if not permission.requires_confirmation or request.confirmed:
            result = dispatcher.dispatch(intent)
        response = CommandResponse(intent=intent, permission=permission, result=result)
        return command_response_to_dict(response)

    # --- Voice ---
    @app.post("/voice/transcribe")
    def voice_transcribe() -> dict[str, Any]:
        from app.actions.voice import record_and_transcribe
        try:
            text = record_and_transcribe()
            return {"success": True, "text": text}
        except Exception as exc:
            return {"success": False, "text": "", "error": str(exc)}

    # --- Browser snapshot (from extension) ---
    @app.post("/browser/snapshot")
    def browser_snapshot(request: BrowserSnapshotRequest) -> dict[str, Any]:
        captured_at = datetime.utcnow()
        items = [
            SnapshotItem(
                app_name=request.browser.title(),
                title=f"{tab.title}{' [active]' if tab.active else ''}",
                url=tab.url,
                item_type="browser_tab",
                process_name=request.browser.lower(),
                executable_path=None,
                created_at=captured_at,
            )
            for tab in request.tabs
        ]
        record = repository.save_snapshot(items)
        logger.info(
            "Saved browser snapshot #%s with %s tab(s) from %s.",
            record.snapshot_id,
            len(record.items),
            request.browser,
        )
        return {
            "success": True,
            "snapshot_id": record.snapshot_id,
            "browser": request.browser,
            "tab_count": len(record.items),
        }

    # --- Tracked apps ---
    @app.get("/tracked-apps")
    def list_tracked_apps() -> dict[str, Any]:
        processes = repository.list_tracked_processes()
        return {
            "tracked_apps": [
                {
                    "process_name": p.process_name,
                    "executable_path": p.executable_path,
                    "window_title": p.window_title,
                }
                for p in processes
            ]
        }

    @app.post("/tracked-apps")
    def save_tracked_apps(apps: list[TrackedProcessRequest]) -> dict[str, Any]:
        processes = [
            TrackedProcess(
                process_name=a.process_name,
                executable_path=a.executable_path,
                window_title=a.window_title,
                created_at=datetime.utcnow(),
            )
            for a in apps
        ]
        repository.replace_tracked_processes(processes)
        return {"success": True, "count": len(processes)}

    # --- Running processes ---
    @app.get("/running-processes")
    def running_processes() -> dict[str, Any]:
        import psutil
        procs = []
        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                info = proc.info
                procs.append({"pid": info["pid"], "name": info["name"], "exe": info["exe"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"processes": procs}

    # --- Auto-snapshot toggle ---
    @app.get("/settings/auto-snapshot")
    def get_auto_snapshot() -> dict[str, Any]:
        return {"enabled": auto_snapshot.is_active}

    @app.post("/settings/auto-snapshot")
    def set_auto_snapshot(body: dict) -> dict[str, Any]:
        enabled = body.get("enabled", True)
        if enabled:
            auto_snapshot.enable()
        else:
            auto_snapshot.disable()
        return {"enabled": auto_snapshot.is_active}

    # --- Settings (persistent) ---
    @app.get("/settings")
    def get_settings() -> dict[str, Any]:
        from app.config import get_setting
        key = get_setting("gemini_api_key", "")
        return {
            "gemini_api_key": ("*" * (len(key) - 4) + key[-4:]) if len(key) > 4 else ("*" * len(key)),
            "gemini_api_key_set": bool(key),
        }

    @app.post("/settings")
    def save_settings_endpoint(body: dict) -> dict[str, Any]:
        from app import config
        from app.config import save_settings
        patch = {}
        if "gemini_api_key" in body:
            patch["gemini_api_key"] = body["gemini_api_key"]
            # 런타임에도 즉시 반영
            config.GEMINI_API_KEY = body["gemini_api_key"]
        save_settings(patch)
        return {"success": True}

    # --- Wake word ---
    @app.get("/settings/wakeword")
    def get_wakeword() -> dict[str, Any]:
        return {"enabled": wake_word.is_active}

    @app.post("/settings/wakeword")
    def set_wakeword(body: dict) -> dict[str, Any]:
        if body.get("enabled", False):
            wake_word.start()
        else:
            wake_word.stop()
        return {"enabled": wake_word.is_active}

    @app.get("/wakeword/poll")
    def poll_wakeword() -> dict[str, Any]:
        """프론트엔드가 800ms마다 폴링. triggered=True면 음성 명령 모드 진입."""
        return {"triggered": wake_word.poll_and_clear()}

    return app


def _snapshot_to_dict(record: Any) -> dict[str, Any]:
    return {
        "snapshot_id": record.snapshot_id,
        "created_at": record.created_at.isoformat(),
        "items": [
            {
                "app_name": item.app_name,
                "title": item.title,
                "url": item.url,
                "path": item.path,
                "item_type": item.item_type,
                "process_name": item.process_name,
                "executable_path": item.executable_path,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in record.items
        ],
    }
