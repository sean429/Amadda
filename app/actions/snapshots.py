from __future__ import annotations

import os

from app.actions.snapshot_collectors import (
    NoopSnapshotCollector,
    SnapshotCollector,
    WindowsSnapshotCollector,
)
from app.db.sqlite import SnapshotRepository
from app.models import ActionResult, RunningProcess, SnapshotItem, TrackedProcess


class SnapshotActionService:
    def __init__(self, repository: SnapshotRepository) -> None:
        self.repository = repository

    def _build_collector(self) -> SnapshotCollector:
        if os.name == "nt":
            return WindowsSnapshotCollector(self.repository.list_tracked_processes())
        return NoopSnapshotCollector()

    def collect_snapshot_items(self) -> list[SnapshotItem]:
        return self._build_collector().collect().items

    def list_running_processes(self) -> list[RunningProcess]:
        return self._build_collector().list_running_processes()

    def save_tracked_processes(self, tracked_processes: list[TrackedProcess]) -> None:
        self.repository.replace_tracked_processes(tracked_processes)

    def list_tracked_processes(self) -> list[TrackedProcess]:
        return self.repository.list_tracked_processes()

    def save_snapshot(self) -> ActionResult:
        collection = self._build_collector().collect()
        items = collection.items
        record = self.repository.save_snapshot(items)
        return ActionResult(
            success=True,
            message=f"Saved snapshot #{record.snapshot_id} with {len(record.items)} item(s).",
            data={
                "snapshot_id": record.snapshot_id,
                "item_count": len(record.items),
                "logs": collection.logs,
                "items": [
                    {
                        "app_name": item.app_name,
                        "title": item.title,
                        "url": item.url,
                        "item_type": item.item_type,
                        "process_name": item.process_name,
                        "executable_path": item.executable_path,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in record.items[:25]
                ],
            },
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
                        "item_type": item.item_type,
                        "process_name": item.process_name,
                        "executable_path": item.executable_path,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in record.items
                ],
            },
        )
