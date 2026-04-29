from __future__ import annotations

import threading
import time

import uvicorn
import webview

from app.api.server import create_app
from app.config import API_HOST, API_PORT
from app.services import auto_snapshot


def _start_server() -> None:
    uvicorn.run(
        create_app(),
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
    )


def _wait_for_server(timeout: float = 10.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{API_HOST}:{API_PORT}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.15)
    return False


def run_desktop_app() -> int:
    server_thread = threading.Thread(target=_start_server, daemon=True)
    server_thread.start()

    auto_snapshot.start()

    if not _wait_for_server():
        print("ERROR: Amadda API server failed to start.")
        return 1

    webview.create_window(
        title="Amadda",
        url=f"http://{API_HOST}:{API_PORT}/",
        width=820,
        height=640,
        min_size=(520, 400),
        resizable=True,
        background_color="#1a2420",
    )
    webview.start(debug=False)
    return 0
