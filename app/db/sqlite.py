from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.config import SNAPSHOT_RETENTION_MAX
from app.models import SnapshotItem, SnapshotRecord, TrackedProcess


class SnapshotRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS snapshot_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    item_type TEXT NOT NULL DEFAULT 'application',
                    process_name TEXT,
                    executable_path TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tracked_processes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_name TEXT NOT NULL,
                    executable_path TEXT,
                    window_title TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            existing_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(snapshot_items)").fetchall()
            }
            if "item_type" not in existing_columns:
                connection.execute(
                    "ALTER TABLE snapshot_items ADD COLUMN item_type TEXT NOT NULL DEFAULT 'application'"
                )
            if "process_name" not in existing_columns:
                connection.execute("ALTER TABLE snapshot_items ADD COLUMN process_name TEXT")
            if "executable_path" not in existing_columns:
                connection.execute("ALTER TABLE snapshot_items ADD COLUMN executable_path TEXT")
            if "path" not in existing_columns:
                connection.execute("ALTER TABLE snapshot_items ADD COLUMN path TEXT")
            connection.commit()

    def list_tracked_processes(self) -> list[TrackedProcess]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT process_name, executable_path, window_title, created_at
                FROM tracked_processes
                ORDER BY process_name COLLATE NOCASE ASC, id ASC
                """
            ).fetchall()

        return [
            TrackedProcess(
                process_name=row["process_name"],
                executable_path=row["executable_path"],
                window_title=row["window_title"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def replace_tracked_processes(self, tracked_processes: list[TrackedProcess]) -> None:
        created_at = datetime.utcnow().isoformat()
        with self.connect() as connection:
            connection.execute("DELETE FROM tracked_processes")
            connection.executemany(
                """
                INSERT INTO tracked_processes (
                    process_name,
                    executable_path,
                    window_title,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        tracked_process.process_name,
                        tracked_process.executable_path,
                        tracked_process.window_title,
                        (tracked_process.created_at or datetime.fromisoformat(created_at)).isoformat(),
                    )
                    for tracked_process in tracked_processes
                ],
            )
            connection.commit()

    def save_snapshot(self, items: list[SnapshotItem]) -> SnapshotRecord:
        created_at = datetime.utcnow().isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO snapshots (created_at) VALUES (?)",
                (created_at,),
            )
            snapshot_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO snapshot_items (
                    snapshot_id,
                    app_name,
                    title,
                    url,
                    path,
                    item_type,
                    process_name,
                    executable_path,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        item.app_name,
                        item.title,
                        item.url,
                        item.path,
                        item.item_type,
                        item.process_name,
                        item.executable_path,
                        (item.created_at or datetime.utcnow()).isoformat(),
                    )
                    for item in items
                ],
            )
            self._prune_old_snapshots(connection, SNAPSHOT_RETENTION_MAX)
            connection.commit()
        return SnapshotRecord(
            snapshot_id=snapshot_id,
            created_at=datetime.fromisoformat(created_at),
            items=items,
        )

    def _prune_old_snapshots(self, connection: sqlite3.Connection, keep_latest: int) -> None:
        if keep_latest <= 0:
            return

        cutoff_row = connection.execute(
            """
            SELECT id
            FROM snapshots
            ORDER BY id DESC
            LIMIT 1 OFFSET ?
            """,
            (keep_latest - 1,),
        ).fetchone()
        if cutoff_row is None:
            return

        cutoff_id = int(cutoff_row["id"])
        connection.execute("DELETE FROM snapshots WHERE id < ?", (cutoff_id,))

    def get_recent_snapshots(self, n: int = 3) -> list[SnapshotRecord]:
        with self.connect() as connection:
            snapshot_rows = connection.execute(
                "SELECT id, created_at FROM snapshots ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
            if not snapshot_rows:
                return []

            snapshot_ids = [row["id"] for row in snapshot_rows]
            placeholders = ",".join("?" * len(snapshot_ids))
            item_rows = connection.execute(
                f"""
                SELECT snapshot_id, app_name, title, url, path, item_type,
                       process_name, executable_path, created_at
                FROM snapshot_items
                WHERE snapshot_id IN ({placeholders})
                ORDER BY snapshot_id DESC, id ASC
                """,
                snapshot_ids,
            ).fetchall()

        items_by_snapshot: dict[int, list[SnapshotItem]] = {row["id"]: [] for row in snapshot_rows}
        for row in item_rows:
            items_by_snapshot[row["snapshot_id"]].append(
                SnapshotItem(
                    app_name=row["app_name"],
                    title=row["title"],
                    url=row["url"],
                    path=row["path"],
                    item_type=row["item_type"],
                    process_name=row["process_name"],
                    executable_path=row["executable_path"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )

        return [
            SnapshotRecord(
                snapshot_id=int(row["id"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                items=items_by_snapshot[row["id"]],
            )
            for row in snapshot_rows
        ]

    def get_latest_browser_tab_items(self) -> list[SnapshotItem]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT si.app_name, si.title, si.url, si.path, si.item_type,
                       si.process_name, si.executable_path, si.created_at
                FROM snapshot_items si
                INNER JOIN (
                    SELECT snapshot_id
                    FROM snapshot_items
                    WHERE item_type = 'browser_tab'
                    ORDER BY snapshot_id DESC
                    LIMIT 1
                ) latest ON si.snapshot_id = latest.snapshot_id
                WHERE si.item_type = 'browser_tab'
                ORDER BY si.id ASC
                """
            ).fetchall()
        return [
            SnapshotItem(
                app_name=row["app_name"],
                title=row["title"],
                url=row["url"],
                path=row["path"],
                item_type=row["item_type"],
                process_name=row["process_name"],
                executable_path=row["executable_path"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def get_latest_snapshot(self) -> SnapshotRecord | None:
        with self.connect() as connection:
            snapshot_row = connection.execute(
                "SELECT id, created_at FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot_row is None:
                return None

            item_rows = connection.execute(
                """
                SELECT app_name, title, url, path, item_type, process_name, executable_path, created_at
                FROM snapshot_items
                WHERE snapshot_id = ?
                ORDER BY id ASC
                """,
                (snapshot_row["id"],),
            ).fetchall()

        items = [
            SnapshotItem(
                app_name=row["app_name"],
                title=row["title"],
                url=row["url"],
                path=row["path"],
                item_type=row["item_type"],
                process_name=row["process_name"],
                executable_path=row["executable_path"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in item_rows
        ]
        return SnapshotRecord(
            snapshot_id=int(snapshot_row["id"]),
            created_at=datetime.fromisoformat(snapshot_row["created_at"]),
            items=items,
        )
