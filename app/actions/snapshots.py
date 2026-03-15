from __future__ import annotations

from datetime import datetime

from app.db.sqlite import SnapshotRepository
from app.models import ActionResult, SnapshotItem


class SnapshotActionService:
    def __init__(self, repository: SnapshotRepository) -> None:
        self.repository = repository

    def collect_snapshot_items(self) -> list[SnapshotItem]:
        # Placeholder source for the MVP. Windows app/window discovery can be
        # added later with pywinauto, pygetwindow, or browser extension data.
        return [
            SnapshotItem(
                app_name="BrowserStub",
                title="Amadda project board",
                url="https://example.com/amadda",
                created_at=datetime.utcnow(),
            ),
            SnapshotItem(
                app_name="EditorStub",
                title="README.md",
                url=None,
                created_at=datetime.utcnow(),
            ),
        ]

    def save_snapshot(self) -> ActionResult:
        items = self.collect_snapshot_items()
        record = self.repository.save_snapshot(items)
        return ActionResult(
            success=True,
            message=f"Saved snapshot #{record.snapshot_id} with {len(record.items)} item(s).",
            data={"snapshot_id": record.snapshot_id},
        )

    def latest_snapshot_summary(self) -> ActionResult:
        record = self.repository.get_latest_snapshot()
        if record is None:
            return ActionResult(success=False, message="No snapshots are available yet.")
        return ActionResult(
            success=True,
            message=f"Loaded latest snapshot #{record.snapshot_id}.",
            data={
                "snapshot_id": record.snapshot_id,
                "created_at": record.created_at.isoformat(),
                "items": [
                    {
                        "app_name": item.app_name,
                        "title": item.title,
                        "url": item.url,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in record.items
                ],
            },
        )
