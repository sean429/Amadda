from __future__ import annotations

import threading

from app.actions.snapshots import SnapshotActionService
from app.config import AUTO_SNAPSHOT_INTERVAL_MINUTES, DB_PATH
from app.db.sqlite import SnapshotRepository
from app.dispatcher.service import ActionDispatcher
from app.intents.parser import RuleBasedIntentParser
from app.permissions.service import PermissionService


repository = SnapshotRepository(DB_PATH)
snapshot_actions = SnapshotActionService(repository)
parser = RuleBasedIntentParser()
permission_service = PermissionService()
dispatcher = ActionDispatcher(repository)


class AutoSnapshotScheduler:
    def __init__(self) -> None:
        self._enabled = True
        self._timer: threading.Timer | None = None

    def start(self) -> None:
        self._schedule()

    def enable(self) -> None:
        if not self._enabled:
            self._enabled = True
            self._schedule()

    def disable(self) -> None:
        self._enabled = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule(self) -> None:
        if self._enabled:
            self._timer = threading.Timer(
                AUTO_SNAPSHOT_INTERVAL_MINUTES * 60,
                self._run,
            )
            self._timer.daemon = True
            self._timer.start()

    def _run(self) -> None:
        try:
            snapshot_actions.save_snapshot()
        except Exception:
            pass
        self._schedule()

    @property
    def is_active(self) -> bool:
        return self._enabled


auto_snapshot = AutoSnapshotScheduler()
