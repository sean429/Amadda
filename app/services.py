from __future__ import annotations

from app.config import DB_PATH
from app.db.sqlite import SnapshotRepository
from app.dispatcher.service import ActionDispatcher
from app.intents.parser import RuleBasedIntentParser
from app.permissions.service import PermissionService


repository = SnapshotRepository(DB_PATH)
parser = RuleBasedIntentParser()
permission_service = PermissionService()
dispatcher = ActionDispatcher(repository)
