from __future__ import annotations

import platform
import subprocess

from app.models import ActionResult


class SystemActionService:
    def __init__(self) -> None:
        self.is_windows = platform.system().lower() == "windows"

    def sleep(self) -> ActionResult:
        if not self.is_windows:
            return ActionResult(
                success=True,
                message="Sleep requested. Non-Windows environment detected, so this is a safe stub.",
            )

        try:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                check=True,
            )
        except Exception as exc:
            return ActionResult(success=False, message=f"Sleep failed: {exc}")
        return ActionResult(success=True, message="System sleep command issued.")

    def shutdown(self) -> ActionResult:
        if not self.is_windows:
            return ActionResult(
                success=True,
                message="Shutdown requested. Non-Windows environment detected, so this is a safe stub.",
            )

        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        except Exception as exc:
            return ActionResult(success=False, message=f"Shutdown failed: {exc}")
        return ActionResult(success=True, message="System shutdown command issued.")
