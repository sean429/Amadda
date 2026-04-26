from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
from csv import reader
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

try:
    import psutil
except ImportError:  # pragma: no cover - dependency availability varies by machine.
    psutil = None

from app.models import RunningProcess, SnapshotItem, TrackedProcess


def _load_vscode_workspace_paths() -> dict[str, str]:
    """VS Code storage.json에서 폴더명 → 실제 경로 매핑을 반환한다."""
    storage_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "storage.json"
    if not storage_path.exists():
        return {}
    try:
        with open(storage_path, encoding="utf-8") as f:
            data = json.load(f)
        folders = data.get("backupWorkspaces", {}).get("folders", [])
        result: dict[str, str] = {}
        for folder in folders:
            uri = folder.get("folderUri", "")
            if not uri.startswith("file:///"):
                continue
            decoded = unquote(uri[len("file:///"):]).replace("/", "\\")
            folder_name = Path(decoded).name
            result[folder_name.lower()] = decoded
        return result
    except Exception:
        return {}


def _parse_vscode_title(title: str) -> tuple[str, str] | None:
    """'파일명 - 프로젝트명 - Visual Studio Code' 형식에서 (파일명, 프로젝트명)을 반환한다."""
    suffix = " - Visual Studio Code"
    if not title.endswith(suffix):
        return None
    body = title[: -len(suffix)]
    # 앞에 ● (unsaved indicator) 제거
    body = re.sub(r"^[●•]\s*", "", body)
    parts = [p.strip() for p in body.split(" - ")]
    if len(parts) >= 2:
        return parts[-2], parts[-1]  # 파일명, 프로젝트명 (역순에서)
    if len(parts) == 1:
        return "", parts[0]
    return None


def _parse_word_title(title: str) -> str | None:
    """'문서명 - Word' 또는 '문서명 - Microsoft Word' 형식에서 문서명을 반환한다."""
    for suffix in (" - Microsoft Word", " - Word"):
        if title.endswith(suffix):
            doc = title[: -len(suffix)].strip()
            doc = re.sub(r"\s*\[.*?\]", "", doc).strip()
            return doc if doc else None
    return None


@dataclass(slots=True)
class SnapshotCollectionResult:
    items: list[SnapshotItem] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class SnapshotCollector:
    def collect(self) -> SnapshotCollectionResult:
        raise NotImplementedError

    def list_running_processes(self) -> list[RunningProcess]:
        raise NotImplementedError


class NoopSnapshotCollector(SnapshotCollector):
    def collect(self) -> SnapshotCollectionResult:
        return SnapshotCollectionResult(
            items=[],
            logs=["Snapshot collection is not supported on this platform yet."],
        )

    def list_running_processes(self) -> list[RunningProcess]:
        return []


class WindowsSnapshotCollector(SnapshotCollector):
    IGNORED_PROCESS_NAMES = {
        "System Idle Process",
        "System",
        "Registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "LsaIso.exe",
        "fontdrvhost.exe",
        "dwm.exe",
        "svchost.exe",
    }

    ALWAYS_INCLUDE_PROCESS_NAMES = {
        "explorer.exe",
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "WindowsTerminal.exe",
        "notepad.exe",
        "chrome.exe",
        "msedge.exe",
        "Code.exe",
        "devenv.exe",
        "pycharm64.exe",
        "python.exe",
        "pythonw.exe",
    }

    IGNORED_PROCESS_SUFFIXES = (
        "service.exe",
        "svc.exe",
        "tray.exe",
        "launcher.exe",
        "container.exe",
    )

    IGNORED_PROCESS_KEYWORDS = (
        "security",
        "defender",
        "launcher",
        "webview",
        "responder",
        "monitor",
        "updater",
        "update",
        "vanguard",
    )

    IGNORED_PATH_KEYWORDS = (
        "\\windows\\system32\\",
        "\\windows\\imgsf",
        "\\driverstore\\",
        "\\programdata\\microsoft\\windows defender\\",
        "\\bonjour service\\",
        "\\nxweb\\",
        "\\crossex\\",
        "\\clicktorun\\",
        "\\gigabyte\\",
        "\\nexon\\",
        "\\riot vanguard\\",
    )

    def __init__(self, tracked_processes: list[TrackedProcess] | None = None) -> None:
        self.tracked_processes = tracked_processes or []

    def collect(self) -> SnapshotCollectionResult:
        collected_at = datetime.utcnow()
        logs: list[str] = []
        window_titles_by_pid = self._collect_window_titles(logs)
        process_infos = self._iter_processes(logs)

        if not self.tracked_processes:
            logs.append("No tracked processes are configured; snapshot collection returned no process items.")
            return SnapshotCollectionResult(items=[], logs=logs)

        # (process_name, executable_path) 기준으로 그룹화 — 서브 프로세스 중복 제거
        groups: dict[tuple[str, str | None], dict] = {}
        ignored_process_count = 0

        for process_info in process_infos:
            pid = process_info["pid"]
            process_name = process_info["name"]
            executable_path = process_info.get("exe")
            visible_titles = window_titles_by_pid.get(pid, [])

            if self._should_ignore_process(process_name, executable_path, visible_titles):
                ignored_process_count += 1
                continue
            if not self._matches_tracked_process(process_name, executable_path, visible_titles):
                continue

            key = (process_name, executable_path)
            if key not in groups:
                groups[key] = {
                    "process_name": process_name,
                    "executable_path": executable_path,
                    "titles": [],
                }
            for title in visible_titles:
                if title not in groups[key]["titles"]:
                    groups[key]["titles"].append(title)

        items: list[SnapshotItem] = []
        process_count = 0
        process_with_windows = 0
        tracked_match_count = len(groups)

        for (process_name, executable_path), group in groups.items():
            visible_titles = group["titles"]
            process_count += 1
            if visible_titles:
                process_with_windows += 1

            app_name = process_name or (Path(executable_path).name if executable_path else "unknown")

            items.append(
                SnapshotItem(
                    app_name=app_name,
                    title=visible_titles[0] if visible_titles else process_name,
                    url=None,
                    item_type="process",
                    process_name=process_name,
                    executable_path=executable_path,
                    created_at=collected_at,
                )
            )

            for title in visible_titles:
                items.append(
                    SnapshotItem(
                        app_name=app_name,
                        title=title,
                        url=None,
                        item_type="window",
                        process_name=process_name,
                        executable_path=executable_path,
                        created_at=collected_at,
                    )
                )

        self._enrich_app_context(items, logs)

        window_item_count = sum(1 for item in items if item.item_type == "window")
        logs.append(f"Ignored {ignored_process_count} process(es) by filter.")
        logs.append(f"Matched {tracked_match_count} tracked process(es).")
        logs.append(f"Collected {process_count} processes after filtering.")
        logs.append(
            f"Collected {window_item_count} visible window title(s) across {process_with_windows} process(es)."
        )
        return SnapshotCollectionResult(items=items, logs=logs)

    def _enrich_app_context(self, items: list[SnapshotItem], logs: list[str]) -> None:
        """VS Code / Word 창 아이템에 workspace/문서 경로를 보강한다."""
        vscode_paths = _load_vscode_workspace_paths()
        enriched = 0

        for item in items:
            if item.item_type != "window":
                continue

            if item.process_name in ("Code.exe", "code.exe"):
                parsed = _parse_vscode_title(item.title)
                if parsed:
                    file_name, project_name = parsed
                    workspace_path = vscode_paths.get(project_name.lower())
                    if workspace_path:
                        item.path = workspace_path
                        enriched += 1
                    elif project_name:
                        item.path = project_name
                        enriched += 1

            elif item.process_name in ("WINWORD.EXE", "winword.exe"):
                doc_name = _parse_word_title(item.title)
                if doc_name:
                    item.path = doc_name
                    enriched += 1

        if enriched:
            logs.append(f"Enriched {enriched} app context item(s) with workspace/document info.")

    def list_running_processes(self) -> list[RunningProcess]:
        logs: list[str] = []
        window_titles_by_pid = self._collect_window_titles(logs)
        running_processes: list[RunningProcess] = []

        for process_info in self._iter_processes(logs):
            pid = int(process_info["pid"])
            process_name = str(process_info["name"])
            executable_path = process_info.get("exe")
            visible_titles = window_titles_by_pid.get(pid, [])
            primary_title = visible_titles[0] if visible_titles else None

            running_processes.append(
                RunningProcess(
                    pid=pid,
                    process_name=process_name,
                    window_title=primary_title,
                    executable_path=str(executable_path) if executable_path else None,
                    visible_window_titles=list(visible_titles),
                )
            )

        running_processes.sort(
            key=lambda process: (
                0 if process.window_title else 1,
                0
                if not self._should_ignore_process(
                    process.process_name,
                    process.executable_path,
                    process.visible_window_titles,
                )
                else 1,
                process.process_name.lower(),
                process.pid,
            )
        )
        return running_processes

    def _should_ignore_process(
        self,
        process_name: str,
        executable_path: str | None,
        visible_titles: list[str],
    ) -> bool:
        if visible_titles:
            return False
        if process_name in self.ALWAYS_INCLUDE_PROCESS_NAMES:
            return False
        normalized_name = process_name.lower()
        if process_name in self.IGNORED_PROCESS_NAMES:
            return True
        if normalized_name.startswith("pid-"):
            return True
        if process_name in {"MemCompression"}:
            return True
        if normalized_name.endswith(self.IGNORED_PROCESS_SUFFIXES):
            return True
        if any(keyword in normalized_name for keyword in self.IGNORED_PROCESS_KEYWORDS):
            return True
        if executable_path:
            normalized_path = executable_path.lower()
            if any(keyword in normalized_path for keyword in self.IGNORED_PATH_KEYWORDS):
                return True
        return False

    def _iter_processes(self, logs: list[str]) -> list[dict[str, str | int | None]]:
        if psutil is not None:
            return self._iter_processes_with_psutil(logs)

        logs.append("psutil is not installed; falling back to tasklist for process names.")
        return self._iter_processes_with_tasklist(logs)

    def _iter_processes_with_psutil(
        self, logs: list[str]
    ) -> list[dict[str, str | int | None]]:
        processes: list[dict[str, str | int | None]] = []
        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                processes.append(
                    {
                        "pid": int(process.info["pid"]),
                        "name": process.info.get("name") or f"pid-{process.pid}",
                        "exe": process.info.get("exe") or None,
                    }
                )
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                logs.append(f"Skipped process metadata for pid={process.pid}: access denied")
                continue
        return processes

    def _iter_processes_with_tasklist(
        self, logs: list[str]
    ) -> list[dict[str, str | int | None]]:
        try:
            completed = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as exc:
            logs.append(f"tasklist fallback failed: {exc}")
            return []

        processes: list[dict[str, str | int | None]] = []
        for row in reader(completed.stdout.splitlines()):
            if len(row) < 2:
                continue
            pid_text = row[1].strip()
            if not pid_text.isdigit():
                continue
            processes.append(
                {
                    "pid": int(pid_text),
                    "name": row[0].strip() or f"pid-{pid_text}",
                    "exe": None,
                }
            )
        return processes

    def _collect_window_titles(self, logs: list[str]) -> dict[int, list[str]]:
        if os.name != "nt":
            return {}

        user32 = ctypes.windll.user32
        titles_by_pid: dict[int, list[str]] = {}

        enum_windows_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd: int, lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if not title:
                return True

            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == 0:
                return True

            titles = titles_by_pid.setdefault(int(pid.value), [])
            if title not in titles:
                titles.append(title)
            return True

        try:
            user32.EnumWindows(enum_windows_proc(callback), 0)
        except Exception as exc:
            logs.append(f"Visible window enumeration failed: {exc}")
            return {}

        logs.append(
            f"Enumerated {sum(len(titles) for titles in titles_by_pid.values())} visible window title(s)."
        )
        return titles_by_pid

    def _matches_tracked_process(
        self,
        process_name: str,
        executable_path: str | None,
        visible_titles: list[str],
    ) -> bool:
        normalized_path = executable_path.casefold() if executable_path else None
        visible_title_set = {title.casefold() for title in visible_titles}

        for tracked_process in self.tracked_processes:
            if tracked_process.process_name != process_name:
                continue
            if tracked_process.executable_path:
                if not normalized_path:
                    continue
                if tracked_process.executable_path.casefold() != normalized_path:
                    continue
            if tracked_process.window_title:
                if tracked_process.window_title.casefold() not in visible_title_set:
                    continue
            return True
        return False
