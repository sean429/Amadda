from __future__ import annotations

from app.models import Intent, PermissionDecision


class PermissionService:
    DANGEROUS_INTENTS = {
        "sleep": "System sleep changes the current desktop session state.",
        "shutdown": "System shutdown closes the current desktop session.",
    }

    def evaluate(self, intent: Intent) -> PermissionDecision:
        reason = self.DANGEROUS_INTENTS.get(intent.name)
        return PermissionDecision(
            requires_confirmation=intent.requires_confirmation or reason is not None,
            reason=reason,
        )
