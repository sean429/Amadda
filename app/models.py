from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SnapshotItem:
    app_name: str
    title: str
    url: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class SnapshotRecord:
    snapshot_id: int
    created_at: datetime
    items: list[SnapshotItem] = field(default_factory=list)


@dataclass(slots=True)
class Intent:
    intent: str
    params: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    raw_text: str = ""

    @property
    def name(self) -> str:
        return self.intent

    @property
    def parameters(self) -> dict[str, Any]:
        return self.params


@dataclass(slots=True)
class PermissionDecision:
    requires_confirmation: bool
    reason: str | None = None


@dataclass(slots=True)
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CommandResponse:
    intent: Intent
    permission: PermissionDecision
    result: ActionResult | None = None
