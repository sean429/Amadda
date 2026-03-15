from __future__ import annotations

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

    def restore_snapshot_urls(self, snapshot: SnapshotRecord) -> ActionResult:
        opened_urls: list[str] = []
        for item in snapshot.items:
            if item.url:
                webbrowser.open(item.url)
                opened_urls.append(item.url)
        if not opened_urls:
            return ActionResult(
                success=True,
                message="Snapshot restored. No URLs were available to reopen.",
                data={"snapshot_id": snapshot.snapshot_id},
            )
        return ActionResult(
            success=True,
            message=f"Reopened {len(opened_urls)} URL(s) from the latest snapshot.",
            data={"snapshot_id": snapshot.snapshot_id, "urls": opened_urls},
        )
