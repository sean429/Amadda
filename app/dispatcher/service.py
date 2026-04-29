from __future__ import annotations

from app.actions.browser import BrowserActionService
from app.actions.llm import LLMActionService
from app.actions.snapshots import SnapshotActionService
from app.actions.system import SystemActionService
from app.db.sqlite import SnapshotRepository
from app.models import ActionResult, Intent


class ActionDispatcher:
    def __init__(self, repository: SnapshotRepository) -> None:
        self.system_actions = SystemActionService()
        self.browser_actions = BrowserActionService()
        self.snapshot_actions = SnapshotActionService(repository)
        self.llm_actions = LLMActionService()
        self.repository = repository

    _INTRO = (
        "저는 **아맞다**입니다. 당신 곁에서 작업 흐름을 조용히 기억하는 AI 비서예요.\n"
        "자리를 비운 사이 무엇을 하고 있었는지 잊으셨나요? 걱정 마세요, 제가 다 기억하고 있을게요.\n"
        "브라우저 탭, 열어둔 앱, 작업 중이던 파일까지 — 명령 한 마디면 지금 하던 일로 바로 돌아갈 수 있어요.\n"
        "음성으로 말씀하셔도 되고, 텍스트로 입력하셔도 돼요.\n"
        "아, 맞다 — 하고 생각나실 때 언제든 불러주세요."
    )

    def dispatch(self, intent: Intent) -> ActionResult:
        if intent.intent == "introduce":
            return ActionResult(success=True, message=self._INTRO)
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
            return self.browser_actions.restore_snapshot(latest)
        if intent.intent == "summarize":
            snapshots = self.repository.get_recent_snapshots(n=3)
            if not snapshots:
                return ActionResult(success=False, message="저장된 스냅샷이 없습니다.")
            return self.llm_actions.summarize_recent_snapshots(snapshots)
        if intent.intent == "open_app":
            return self.system_actions.launch_app(intent.params["app"])
        return ActionResult(success=False, message=f"Unknown intent: {intent.raw_text}")
