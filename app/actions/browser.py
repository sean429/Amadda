from __future__ import annotations

import os
import subprocess
import webbrowser

from app.models import ActionResult, SnapshotRecord


class BrowserActionService:
    def open_url(self, url: str) -> ActionResult:
        opened = webbrowser.open(url)
        return ActionResult(
            success=opened,
            message=f"Opened URL: {url}" if opened else f"Failed to open URL: {url}",
            data={"url": url},
        )

    def restore_snapshot(self, snapshot: SnapshotRecord) -> ActionResult:
        opened_urls: list[str] = []
        opened_apps: list[str] = []

        for item in snapshot.items:
            if item.url:
                webbrowser.open(item.url)
                opened_urls.append(item.url)

        vscode_paths: set[str] = set()
        for item in snapshot.items:
            if item.item_type == "window" and item.process_name in ("Code.exe", "code.exe"):
                if item.path and os.path.isabs(item.path):
                    vscode_paths.add(item.path)

        for path in vscode_paths:
            try:
                subprocess.Popen(["code", path], shell=False)
                opened_apps.append(f"VS Code: {path}")
            except Exception:
                pass

        total = len(opened_urls) + len(opened_apps)
        if total == 0:
            return ActionResult(
                success=True,
                message="복구할 항목이 없습니다. (저장된 URL 또는 VS Code 경로 없음)",
                data={"snapshot_id": snapshot.snapshot_id},
            )

        parts = []
        if opened_urls:
            parts.append(f"브라우저 탭 {len(opened_urls)}개")
        if opened_apps:
            parts.append(f"VS Code 워크스페이스 {len(vscode_paths)}개")

        return ActionResult(
            success=True,
            message=f"복구 완료: {', '.join(parts)}.",
            data={"snapshot_id": snapshot.snapshot_id, "urls": opened_urls, "apps": opened_apps},
        )
