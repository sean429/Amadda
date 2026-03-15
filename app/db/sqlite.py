from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.models import SnapshotItem, SnapshotRecord


class SnapshotRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
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
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id) ON DELETE CASCADE
                );
                """
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
                INSERT INTO snapshot_items (snapshot_id, app_name, title, url, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        item.app_name,
                        item.title,
                        item.url,
                        (item.created_at or datetime.utcnow()).isoformat(),
                    )
                    for item in items
                ],
            )
            connection.commit()
        return SnapshotRecord(
            snapshot_id=snapshot_id,
            created_at=datetime.fromisoformat(created_at),
            items=items,
        )

    def get_latest_snapshot(self) -> SnapshotRecord | None:
        with self.connect() as connection:
            snapshot_row = connection.execute(
                "SELECT id, created_at FROM snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snapshot_row is None:
                return None

            item_rows = connection.execute(
                """
                SELECT app_name, title, url, created_at
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
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in item_rows
        ]
        return SnapshotRecord(
            snapshot_id=int(snapshot_row["id"]),
            created_at=datetime.fromisoformat(snapshot_row["created_at"]),
            items=items,
        )
