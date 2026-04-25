from __future__ import annotations

import sys
import threading
from collections import defaultdict

import uvicorn
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileIconProvider,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.actions.snapshots import SnapshotActionService
from app.api.server import create_app
from app.config import API_HOST, APP_NAME
from app.models import CommandResponse, RunningProcess, TrackedProcess
from app.runtime import select_api_port
from app.services import dispatcher, parser, permission_service, snapshot_actions


class FastAPIServerThread(threading.Thread):
    def __init__(self, port: int) -> None:
        super().__init__(daemon=True)
        self.port = port

    def run(self) -> None:
        app = create_app()
        config = uvicorn.Config(app=app, host=API_HOST, port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        server.install_signal_handlers = lambda: None
        server.run()


class ProcessGroup:
    def __init__(self, process_name: str) -> None:
        self.process_name = process_name
        self.processes: list[RunningProcess] = []

    @property
    def pids_text(self) -> str:
        return ", ".join(str(process.pid) for process in self.processes)

    @property
    def window_titles_text(self) -> str:
        titles: list[str] = []
        for process in self.processes:
            for title in process.visible_window_titles:
                if title not in titles:
                    titles.append(title)
        return " | ".join(titles)

    @property
    def executable_paths_text(self) -> str:
        paths: list[str] = []
        for process in self.processes:
            if process.executable_path and process.executable_path not in paths:
                paths.append(process.executable_path)
        return " | ".join(paths)

    @property
    def visible_count(self) -> int:
        return sum(1 for process in self.processes if process.window_title)

    @property
    def process_count(self) -> int:
        return len(self.processes)


class TrackedAppsDialog(QDialog):
    def __init__(self, snapshot_service: SnapshotActionService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot_service = snapshot_service
        self.groups: list[ProcessGroup] = []
        self.tracked_process_names: set[str] = set()
        self.setWindowTitle("Tracked Apps")
        self.resize(980, 560)
        self._build_ui()
        self._load_tracked_keys()
        self.refresh_processes()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Choose which running apps should be included in future snapshots. "
            "Visible windowed apps are listed first."
        )
        intro.setWordWrap(True)

        refresh_button = QPushButton("Refresh", self)
        refresh_button.clicked.connect(self.refresh_processes)

        controls = QHBoxLayout()
        controls.addWidget(intro)
        controls.addWidget(refresh_button)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Track", "Process Name", "PIDs", "Window Titles", "Executable Paths"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            self,
        )
        buttons.accepted.connect(self._save_selection)
        buttons.rejected.connect(self.reject)

        layout.addLayout(controls)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def _load_tracked_keys(self) -> None:
        self.tracked_process_names = {
            tracked_process.process_name
            for tracked_process in self.snapshot_service.list_tracked_processes()
        }

    def refresh_processes(self) -> None:
        processes = self.snapshot_service.list_running_processes()
        grouped_processes: dict[str, ProcessGroup] = defaultdict(lambda: ProcessGroup(""))

        for process in processes:
            group = grouped_processes.get(process.process_name)
            if group is None:
                group = ProcessGroup(process.process_name)
                grouped_processes[process.process_name] = group
            elif not group.process_name:
                group.process_name = process.process_name
            group.processes.append(process)

        self.groups = sorted(
            grouped_processes.values(),
            key=lambda group: (
                0 if group.visible_count else 1,
                group.process_name.lower(),
            ),
        )
        self.table.setRowCount(len(self.groups))
        icon_provider = QFileIconProvider()

        for row, group in enumerate(self.groups):
            tracked_item = QTableWidgetItem()
            tracked_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            tracked_item.setCheckState(
                Qt.Checked if group.process_name in self.tracked_process_names else Qt.Unchecked
            )
            tracked_item.setData(Qt.UserRole, row)

            label = (
                f"{group.process_name} ({group.process_count})"
                if group.process_count > 1
                else group.process_name
            )
            process_name = QTableWidgetItem(label)
            exe_paths = [p for p in group.executable_paths_text.split(" | ") if p]
            if exe_paths:
                process_name.setIcon(icon_provider.icon(QFileInfo(exe_paths[0])))
            pid = QTableWidgetItem(group.pids_text)
            window_title = QTableWidgetItem(group.window_titles_text)
            executable_path = QTableWidgetItem(group.executable_paths_text)

            if group.visible_count:
                for item in (process_name, pid, window_title, executable_path):
                    item.setToolTip(f"Visible window detected in {group.visible_count} process(es)")

            self.table.setItem(row, 0, tracked_item)
            self.table.setItem(row, 1, process_name)
            self.table.setItem(row, 2, pid)
            self.table.setItem(row, 3, window_title)
            self.table.setItem(row, 4, executable_path)

        self.table.resizeRowsToContents()

    def _save_selection(self) -> None:
        tracked_processes = self._selected_tracked_processes()
        self.snapshot_service.save_tracked_processes(tracked_processes)
        self.accept()

    def _selected_tracked_processes(self) -> list[TrackedProcess]:
        tracked_processes: list[TrackedProcess] = []

        for row, group in enumerate(self.groups):
            item = self.table.item(row, 0)
            if item is None or item.checkState() != Qt.Checked:
                continue

            tracked_processes.append(
                TrackedProcess(
                    process_name=group.process_name,
                    executable_path=None,
                    window_title=None,
                )
            )

        return tracked_processes


class MainWindow(QMainWindow):
    def __init__(self, api_port: int) -> None:
        super().__init__()
        self.api_port = api_port
        self.snapshot_actions = snapshot_actions
        self.setWindowTitle(f"{APP_NAME} MVP")
        self.resize(760, 480)
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)

        intro = QLabel(
            "Text-first MVP for a permission-based desktop assistant. "
            "Voice input can plug in here later via Whisper transcription."
        )
        intro.setWordWrap(True)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText(
            "Try: save snapshot | restore latest snapshot | open https://example.com | sleep"
        )
        self.input.returnPressed.connect(self.handle_submit)

        submit_button = QPushButton("Run", self)
        submit_button.clicked.connect(self.handle_submit)

        tracked_apps_button = QPushButton("Tracked Apps", self)
        tracked_apps_button.clicked.connect(self.open_tracked_apps_dialog)

        input_row = QHBoxLayout()
        input_row.addWidget(self.input)
        input_row.addWidget(submit_button)
        input_row.addWidget(tracked_apps_button)

        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setAcceptRichText(False)

        layout.addWidget(intro)
        layout.addLayout(input_row)
        layout.addWidget(self.log)
        self.setCentralWidget(container)

        self.append_log("Amadda started.")
        self.append_log(f"Local API listening on http://{API_HOST}:{self.api_port}")
        self.append_log(
            "Gemini or another LLM can be inserted after intent parsing once rule-based coverage is no longer enough."
        )

    def open_tracked_apps_dialog(self) -> None:
        dialog = TrackedAppsDialog(self.snapshot_actions, self)
        if dialog.exec() == QDialog.Accepted:
            tracked_count = len(self.snapshot_actions.list_tracked_processes())
            self.append_log(f"Tracked apps updated: {tracked_count} selection(s) saved.")

    def append_log(self, message: str) -> None:
        self.log.append(message)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return

        self.append_log(f"> {text}")
        response = self.execute_command(text)
        self.render_response(response)
        self.input.clear()

    def execute_command(self, text: str) -> CommandResponse:
        intent = parser.parse(text)
        permission = permission_service.evaluate(intent)
        result = None

        if permission.requires_confirmation:
            answer = QMessageBox.question(
                self,
                "Confirm Action",
                permission.reason or "This action requires confirmation.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self.append_log("Action cancelled by user.")
                return CommandResponse(intent=intent, permission=permission, result=None)

        result = dispatcher.dispatch(intent)
        return CommandResponse(intent=intent, permission=permission, result=result)

    def render_response(self, response: CommandResponse) -> None:
        self.append_log(f"Intent: {response.intent.name}")
        if response.permission.requires_confirmation:
            self.append_log("Permission: confirmation required")
        else:
            self.append_log("Permission: auto-approved")

        if response.result is None:
            self.append_log("Result: no action executed")
            return

        status = "ok" if response.result.success else "error"
        self.append_log(f"Result [{status}]: {response.result.message}")
        logs = response.result.data.get("logs")
        if logs:
            for line in logs:
                self.append_log(f"  log: {line}")
        items = response.result.data.get("items")
        if items:
            for item in items:
                self.append_log(
                    "  - "
                    f"{item['item_type']} | "
                    f"{item['app_name']} | "
                    f"{item['title']} | "
                    f"{item.get('process_name') or 'no-process'} | "
                    f"{item.get('executable_path') or 'no-exe'} | "
                    f"{item.get('url') or 'no-url'}"
                )


def run_desktop_app() -> int:
    api_port = select_api_port()
    server_thread = FastAPIServerThread(api_port)
    server_thread.start()

    app = QApplication(sys.argv)
    window = MainWindow(api_port)
    window.show()
    return app.exec()
