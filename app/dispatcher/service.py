from __future__ import annotations

from app.actions.browser import BrowserActionService
from app.actions.snapshots import SnapshotActionService
from app.actions.system import SystemActionService
from app.db.sqlite import SnapshotRepository
from app.models import ActionResult, Intent


class ActionDispatcher:
    def __init__(self, repository: SnapshotRepository) -> None:
        self.system_actions = SystemActionService()
        self.browser_actions = BrowserActionService()
        self.snapshot_actions = SnapshotActionService(repository)
        self.repository = repository

    def dispatch(self, intent: Intent) -> ActionResult:
        if intent.intent == "sleep":
            return self.system_actions.sleep()
        if intent.intent == "shutdown":
            return self.system_actions.shutdown()
        if intent.intent == "open_url":
            return self.browser_actions.open_url(intent.params["url"])
        if intent.intent == "save_snapshot":
            return self.snapshot_actions.save_snapshot()
        if intent.intent == "restore_latest_snapshot":
            latest = self.repository.get_latest_snapshot()
            if latest is None:
                return ActionResult(success=False, message="No snapshots are available yet.")
            return self.browser_actions.restore_snapshot_urls(latest)
        return ActionResult(success=False, message=f"Unknown intent: {intent.raw_text}")
