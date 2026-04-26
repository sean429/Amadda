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

    APP_COMMANDS: dict[str, list[str]] = {
        "word": ["cmd", "/c", "start", "", "winword"],
        "excel": ["cmd", "/c", "start", "", "excel"],
        "powerpoint": ["cmd", "/c", "start", "", "powerpnt"],
        "notepad": ["notepad.exe"],
        "cmd": ["cmd", "/c", "start", "cmd"],
        "powershell": ["cmd", "/c", "start", "", "powershell"],
        "explorer": ["explorer.exe"],
        "vscode": ["cmd", "/c", "start", "", "code"],
    }

    def launch_app(self, app: str) -> ActionResult:
        command = self.APP_COMMANDS.get(app.lower())
        if command is None:
            return ActionResult(success=False, message=f"알 수 없는 앱입니다: {app}")
        try:
            subprocess.Popen(command, shell=False)
        except Exception as exc:
            return ActionResult(success=False, message=f"앱 실행 실패: {exc}")
        return ActionResult(success=True, message=f"{app} 실행 명령을 전송했습니다.")
