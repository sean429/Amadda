from __future__ import annotations

import sys
import threading
from collections import defaultdict
from html import escape

import uvicorn
from PySide6.QtCore import QFileInfo, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileIconProvider,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.actions.snapshots import SnapshotActionService
from app.api.server import create_app
from app.config import API_HOST, APP_NAME, AUTO_SNAPSHOT_INTERVAL_MINUTES, SNAPSHOT_RETENTION_MAX
from app.models import CommandResponse, RunningProcess, SnapshotRecord, TrackedProcess
from app.runtime import select_api_port
from app.services import dispatcher, parser, permission_service, snapshot_actions


# ── Styles ──────────────────────────────────────────────────────────────────

APP_STYLE = """
QMainWindow, QDialog { background-color: #F8F4EF; }
QWidget { background-color: #F8F4EF; color: #1A1A1A; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QTextEdit {
    background-color: #FAFAF8;
    border: 1px solid #E0DAD4;
    border-radius: 8px;
    padding: 10px;
    color: #1A1A1A;
    selection-background-color: #B8D0E8;
}
QLineEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #D8D2CC;
    border-radius: 20px;
    padding: 9px 18px;
    color: #1A1A1A;
    font-size: 13px;
}
QLineEdit:focus { border-color: #6B8CAE; }
QPushButton {
    background-color: #6B8CAE;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton:hover { background-color: #5A7A9A; }
QPushButton:disabled { background-color: #B8C8D8; }
QToolButton {
    background-color: transparent;
    border: none;
    color: #5A5550;
    font-size: 20px;
    padding: 4px 8px;
    border-radius: 6px;
}
QToolButton:hover { background-color: #EDE8E2; }
QTableWidget {
    background-color: #FAFAF8;
    border: 1px solid #E0DAD4;
    border-radius: 6px;
    gridline-color: #EDE8E2;
}
QTableWidget::item:selected { background-color: #D4E4F0; color: #1A1A1A; }
QHeaderView::section {
    background-color: #F0EDE8;
    border: none;
    border-bottom: 1px solid #E0DAD4;
    padding: 6px 10px;
    color: #5A5550;
    font-size: 11px;
    font-weight: 600;
}
QScrollBar:vertical { background: #F0EDE8; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #C8C0B8; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenu {
    background-color: #FAFAF8;
    border: 1px solid #E0DAD4;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 7px 20px; border-radius: 4px; color: #1A1A1A; }
QMenu::item:selected { background-color: #EDE8E2; }
QCheckBox { spacing: 8px; color: #1A1A1A; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid #C8C0B8;
    border-radius: 3px;
    background: white;
}
QCheckBox::indicator:checked { background-color: #6B8CAE; border-color: #6B8CAE; }
"""

_MIC_NORMAL = """
QPushButton {
    background-color: #6B8CAE; color: white; border: none;
    border-radius: 22px; font-size: 18px;
    min-width: 44px; min-height: 44px; max-width: 44px; max-height: 44px;
}
QPushButton:hover { background-color: #5A7A9A; }
QPushButton:disabled { background-color: #B8C8D8; }
"""
_MIC_PULSE_A = """
QPushButton {
    background-color: #A8C4DC; color: white;
    border: 2.5px solid #6B8CAE; border-radius: 22px; font-size: 18px;
    min-width: 44px; min-height: 44px; max-width: 44px; max-height: 44px;
}
"""
_MIC_PULSE_B = """
QPushButton {
    background-color: #6B8CAE; color: white;
    border: 2.5px solid #A8C4DC; border-radius: 22px; font-size: 18px;
    min-width: 44px; min-height: 44px; max-width: 44px; max-height: 44px;
}
"""

_BLOCK_ACCENT   = "#6B8CAE"   # 청화 블루 — 창
_BLOCK_BROWSER  = "#7A9BAE"   # 조금 연한 블루 — 브라우저 탭
_BLOCK_AI       = "#6B8CAE"   # AI 요약
_BLOCK_OK       = "#8BA78A"   # 복구/성공


# ── Workers ──────────────────────────────────────────────────────────────────

class VoiceWorker(QThread):
    status = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def run(self) -> None:
        try:
            from app.actions.voice import record_and_transcribe
            text = record_and_transcribe(on_status=self.status.emit)
            self.finished.emit(text)
        except Exception as exc:
            self.error.emit(str(exc))


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


# ── Process grouping helpers ──────────────────────────────────────────────────

class ProcessGroup:
    def __init__(self, process_name: str) -> None:
        self.process_name = process_name
        self.processes: list[RunningProcess] = []

    @property
    def pids_text(self) -> str:
        return ", ".join(str(p.pid) for p in self.processes)

    @property
    def window_titles_text(self) -> str:
        seen: list[str] = []
        for p in self.processes:
            for t in p.visible_window_titles:
                if t not in seen:
                    seen.append(t)
        return " | ".join(seen)

    @property
    def executable_paths_text(self) -> str:
        seen: list[str] = []
        for p in self.processes:
            if p.executable_path and p.executable_path not in seen:
                seen.append(p.executable_path)
        return " | ".join(seen)

    @property
    def visible_count(self) -> int:
        return sum(1 for p in self.processes if p.window_title)

    @property
    def process_count(self) -> int:
        return len(self.processes)


# ── Dialogs ───────────────────────────────────────────────────────────────────

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

        intro = QLabel("스냅샷에 포함할 앱을 선택하세요. 창이 보이는 앱이 먼저 표시됩니다.")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #7A7370; font-size: 12px;")

        refresh_button = QPushButton("새로고침", self)
        refresh_button.clicked.connect(self.refresh_processes)

        controls = QHBoxLayout()
        controls.addWidget(intro)
        controls.addWidget(refresh_button)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["추적", "프로세스", "PID", "창 제목", "실행 경로"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self._save_selection)
        buttons.rejected.connect(self.reject)

        layout.addLayout(controls)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def _load_tracked_keys(self) -> None:
        self.tracked_process_names = {
            tp.process_name for tp in self.snapshot_service.list_tracked_processes()
        }

    def refresh_processes(self) -> None:
        processes = self.snapshot_service.list_running_processes()
        grouped: dict[str, ProcessGroup] = {}
        for p in processes:
            g = grouped.get(p.process_name)
            if g is None:
                g = ProcessGroup(p.process_name)
                grouped[p.process_name] = g
            g.processes.append(p)

        self.groups = sorted(
            grouped.values(),
            key=lambda g: (0 if g.visible_count else 1, g.process_name.lower()),
        )
        self.table.setRowCount(len(self.groups))
        icon_provider = QFileIconProvider()

        for row, group in enumerate(self.groups):
            tracked_item = QTableWidgetItem()
            tracked_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            tracked_item.setCheckState(
                Qt.Checked if group.process_name in self.tracked_process_names else Qt.Unchecked
            )

            label = (
                f"{group.process_name} ({group.process_count})"
                if group.process_count > 1 else group.process_name
            )
            process_name = QTableWidgetItem(label)
            exe_paths = [p for p in group.executable_paths_text.split(" | ") if p]
            if exe_paths:
                process_name.setIcon(icon_provider.icon(QFileInfo(exe_paths[0])))

            self.table.setItem(row, 0, tracked_item)
            self.table.setItem(row, 1, process_name)
            self.table.setItem(row, 2, QTableWidgetItem(group.pids_text))
            self.table.setItem(row, 3, QTableWidgetItem(group.window_titles_text))
            self.table.setItem(row, 4, QTableWidgetItem(group.executable_paths_text))

        self.table.resizeRowsToContents()

    def _save_selection(self) -> None:
        tracked = []
        for row, group in enumerate(self.groups):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                tracked.append(TrackedProcess(process_name=group.process_name))
        self.snapshot_service.save_tracked_processes(tracked)
        self.accept()


class SnapshotHistoryDialog(QDialog):
    def __init__(self, snapshot_service: SnapshotActionService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot_service = snapshot_service
        self.snapshots: list[SnapshotRecord] = []
        self.setWindowTitle("Snapshot History")
        self.resize(680, 420)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "시각", "열린 창", "브라우저 탭"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        restore_btn = QPushButton("선택 복구", self)
        restore_btn.clicked.connect(self._restore_selected)
        close_btn = QPushButton("닫기", self)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(
            "QPushButton { background-color: #E0DAD4; color: #1A1A1A; }"
            "QPushButton:hover { background-color: #D0CAC4; }"
        )

        btn_row = QHBoxLayout()
        btn_row.addWidget(restore_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout.addWidget(self.table)
        layout.addLayout(btn_row)

    def _load(self) -> None:
        self.snapshots = self.snapshot_service.get_recent_snapshots(n=SNAPSHOT_RETENTION_MAX)
        self.table.setRowCount(len(self.snapshots))
        for row, snap in enumerate(self.snapshots):
            windows = sum(1 for i in snap.items if i.item_type == "window")
            tabs = sum(1 for i in snap.items if i.item_type == "browser_tab")
            self.table.setItem(row, 0, QTableWidgetItem(str(snap.snapshot_id)))
            self.table.setItem(row, 1, QTableWidgetItem(snap.created_at.strftime("%Y-%m-%d %H:%M")))
            self.table.setItem(row, 2, QTableWidgetItem(str(windows)))
            self.table.setItem(row, 3, QTableWidgetItem(str(tabs)))
        self.table.resizeRowsToContents()

    def _restore_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 없음", "복구할 스냅샷을 선택해주세요.")
            return
        result = dispatcher.browser_actions.restore_snapshot(self.snapshots[row])
        QMessageBox.information(self, "복구 결과", result.message)


class SettingsDialog(QDialog):
    def __init__(self, is_auto_enabled: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedWidth(320)
        self._build_ui(is_auto_enabled)

    def _build_ui(self, is_auto_enabled: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        section = QLabel("자동 스냅샷")
        section.setStyleSheet("font-weight: 700; font-size: 13px; color: #2C2C2C;")

        self.auto_toggle = QCheckBox(f"매 {AUTO_SNAPSHOT_INTERVAL_MINUTES}분마다 자동 저장")
        self.auto_toggle.setChecked(is_auto_enabled)

        note = QLabel(f"앱 시작 시 자동으로 활성화됩니다. 최대 {SNAPSHOT_RETENTION_MAX}개 유지.")
        note.setStyleSheet("color: #9A9390; font-size: 11px;")
        note.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(section)
        layout.addWidget(self.auto_toggle)
        layout.addWidget(note)
        layout.addStretch()
        layout.addWidget(buttons)

    @property
    def auto_enabled(self) -> bool:
        return self.auto_toggle.isChecked()


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, api_port: int) -> None:
        super().__init__()
        self.api_port = api_port
        self.snapshot_actions = snapshot_actions
        self.setWindowTitle(APP_NAME)
        self.resize(720, 560)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_state = False

        self._build_ui()
        self._setup_auto_snapshot()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("background-color: #F0EDE8; border-bottom: 1px solid #E0DAD4;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 0, 12, 0)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #2C2C2C; letter-spacing: 1px;")

        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #7EBD8A; font-size: 9px; padding-bottom: 1px;")
        self._dot.setToolTip("자동 스냅샷 활성")

        menu_btn = QToolButton()
        menu_btn.setText("☰")
        menu_btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(menu_btn)
        menu.addAction("Tracked Apps", self.open_tracked_apps_dialog)
        menu.addAction("Snapshot History", self.open_history_dialog)
        menu.addSeparator()
        menu.addAction("Settings", self.open_settings_dialog)
        menu_btn.setMenu(menu)

        hl.addWidget(title)
        hl.addSpacing(6)
        hl.addWidget(self._dot)
        hl.addStretch()
        hl.addWidget(menu_btn)

        # Log / result area
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(
            "QTextEdit { background-color: #FAFAF8; border: none; border-radius: 0;"
            "padding: 12px 16px; }"
        )

        # Bottom bar
        bottom = QWidget()
        bottom.setFixedHeight(70)
        bottom.setStyleSheet("background-color: #F0EDE8; border-top: 1px solid #E0DAD4;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(16, 8, 16, 10)
        bl.setSpacing(4)

        self._voice_status = QLabel("")
        self._voice_status.setStyleSheet("color: #6B8CAE; font-size: 11px; margin-left: 6px;")
        self._voice_status.hide()

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("명령을 입력하세요  —  예: 유튜브 켜줘 / 요약해줘 / 저장해줘")
        self.input.returnPressed.connect(self.handle_submit)

        self.voice_button = QPushButton("🎤")
        self.voice_button.setStyleSheet(_MIC_NORMAL)
        self.voice_button.setFixedSize(44, 44)
        self.voice_button.clicked.connect(self.handle_voice)

        input_row.addWidget(self.input)
        input_row.addWidget(self.voice_button)

        bl.addWidget(self._voice_status)
        bl.addLayout(input_row)

        root.addWidget(header)
        root.addWidget(self.log, 1)
        root.addWidget(bottom)

        self._log_info(f"Amadda 시작됨  —  API http://{API_HOST}:{self.api_port}")

    # ── Auto-snapshot ────────────────────────────────────────────────────────

    def _setup_auto_snapshot(self) -> None:
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(AUTO_SNAPSHOT_INTERVAL_MINUTES * 60 * 1000)
        self._auto_timer.timeout.connect(self._run_auto_snapshot)
        self._auto_timer.start()

    def _toggle_auto_snapshot(self, enable: bool) -> None:
        if enable:
            self._auto_timer.start()
            self._dot.setStyleSheet("color: #7EBD8A; font-size: 9px; padding-bottom: 1px;")
            self._dot.setToolTip("자동 스냅샷 활성")
            self._log_info(f"자동 스냅샷 활성화 ({AUTO_SNAPSHOT_INTERVAL_MINUTES}분 간격)")
        else:
            self._auto_timer.stop()
            self._dot.setStyleSheet("color: #C8C0B8; font-size: 9px; padding-bottom: 1px;")
            self._dot.setToolTip("자동 스냅샷 비활성")
            self._log_info("자동 스냅샷 비활성화")

    def _run_auto_snapshot(self) -> None:
        result = self.snapshot_actions.save_snapshot()
        self._log_info(f"[자동] {result.message}")

    # ── Voice pulse ──────────────────────────────────────────────────────────

    def _start_pulse(self) -> None:
        self._pulse_state = False
        self._pulse_timer.start(600)

    def _stop_pulse(self) -> None:
        self._pulse_timer.stop()
        self.voice_button.setStyleSheet(_MIC_NORMAL)

    def _pulse_tick(self) -> None:
        self._pulse_state = not self._pulse_state
        self.voice_button.setStyleSheet(_MIC_PULSE_A if self._pulse_state else _MIC_PULSE_B)

    # ── Voice handling ───────────────────────────────────────────────────────

    def handle_voice(self) -> None:
        self.voice_button.setEnabled(False)
        self._voice_status.setText("준비 중...")
        self._voice_status.show()
        self._start_pulse()
        self._voice_worker = VoiceWorker()
        self._voice_worker.status.connect(self._voice_status.setText)
        self._voice_worker.finished.connect(self._on_voice_finished)
        self._voice_worker.error.connect(self._on_voice_error)
        self._voice_worker.start()

    def _on_voice_finished(self, text: str) -> None:
        self._stop_pulse()
        self._voice_status.hide()
        self.voice_button.setEnabled(True)
        if text:
            self._log_info(f"🎤 {text}")
            self.input.setText(text)
            self.handle_submit()

    def _on_voice_error(self, message: str) -> None:
        self._stop_pulse()
        self._voice_status.hide()
        self.voice_button.setEnabled(True)
        self._log_info(f"음성 오류: {message}")

    # ── Dialogs ──────────────────────────────────────────────────────────────

    def open_tracked_apps_dialog(self) -> None:
        dialog = TrackedAppsDialog(self.snapshot_actions, self)
        if dialog.exec() == QDialog.Accepted:
            count = len(self.snapshot_actions.list_tracked_processes())
            self._log_info(f"추적 앱 저장됨 ({count}개)")

    def open_history_dialog(self) -> None:
        SnapshotHistoryDialog(self.snapshot_actions, self).exec()

    def open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self._auto_timer.isActive(), self)
        if dialog.exec() == QDialog.Accepted:
            self._toggle_auto_snapshot(dialog.auto_enabled)

    # ── Command handling ─────────────────────────────────────────────────────

    def handle_submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self._append_html(
            f'<div style="margin: 10px 4px 2px;">'
            f'<span style="color: #6B8CAE; font-weight: bold;">›</span>'
            f' <span style="color: #2C2C2C; font-size: 13px;">{escape(text)}</span>'
            f'</div>'
        )
        response = self.execute_command(text)
        self.render_response(response)
        self.input.clear()

    def execute_command(self, text: str) -> CommandResponse:
        intent = parser.parse(text)
        permission = permission_service.evaluate(intent)
        result = None

        if permission.requires_confirmation:
            answer = QMessageBox.question(
                self, "확인",
                permission.reason or "이 작업을 실행하려면 확인이 필요합니다.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self._log_info("취소됨")
                return CommandResponse(intent=intent, permission=permission, result=None)

        result = dispatcher.dispatch(intent)
        return CommandResponse(intent=intent, permission=permission, result=result)

    def render_response(self, response: CommandResponse) -> None:
        if response.result is None:
            return

        if not response.result.success:
            self._log_info(f"오류: {response.result.message}")
            return

        intent = response.intent.intent

        if intent == "summarize":
            self._append_block("AI 요약", [response.result.message], _BLOCK_AI)
            return

        if intent == "save_snapshot":
            items = response.result.data.get("items", [])
            windows, tabs = [], []
            for item in items:
                if item.get("item_type") == "window" and item.get("title"):
                    label = escape(item["title"])
                    if item.get("path"):
                        label += (
                            f' <span style="color:#A0A8B8; font-size:11px;">'
                            f'({escape(item["path"])})</span>'
                        )
                    windows.append(label)
                elif item.get("item_type") == "browser_tab" and item.get("title"):
                    label = escape(item["title"])
                    if item.get("url"):
                        short = escape(item["url"][:60])
                        label += f' <span style="color:#A0A8B8; font-size:11px;">{short}</span>'
                    tabs.append(label)
            if windows:
                self._append_block("열린 창", windows, _BLOCK_ACCENT)
            if tabs:
                self._append_block("브라우저 탭", tabs, _BLOCK_BROWSER)
            if not windows and not tabs:
                self._log_info(response.result.message)
            return

        if intent == "restore_latest_snapshot":
            parts = []
            data = response.result.data
            if data.get("urls"):
                parts.append(f"브라우저 탭 {len(data['urls'])}개")
            if data.get("apps"):
                parts.append(f"VS Code {len(data['apps'])}개")
            msg = ("복구 완료: " + ", ".join(parts)) if parts else response.result.message
            self._append_block("복구", [msg], _BLOCK_OK)
            return

        self._log_info(f"✓ {response.result.message}")

    # ── Log helpers ──────────────────────────────────────────────────────────

    def _log_info(self, message: str) -> None:
        self._append_html(
            f'<div style="color: #9A9390; font-size: 12px; margin: 1px 4px;">'
            f'{escape(message)}</div>'
        )

    def _append_block(self, title: str, lines: list[str], accent: str) -> None:
        rows = "".join(
            f'<div style="margin: 3px 0; color: #2C2C2C; font-size: 12px;">∙ {line}</div>'
            for line in lines
        )
        self._append_html(
            f'<div style="border-left: 3px solid {accent}; background-color: #F0EDE8;'
            f'border-radius: 0 4px 4px 0; padding: 8px 12px; margin: 6px 4px;">'
            f'<div style="color: {accent}; font-size: 10px; font-weight: bold;'
            f'letter-spacing: 0.5px; margin-bottom: 5px;">{escape(title).upper()}</div>'
            f'{rows}</div>'
        )

    def _append_html(self, html: str) -> None:
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log.setTextCursor(cursor)
        self.log.insertHtml(html)
        self.log.insertHtml("<br>")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    # ── Legacy alias (browser snapshot endpoint still calls append_log) ──────

    def append_log(self, message: str) -> None:
        self._log_info(message)


# ── Entry point ───────────────────────────────────────────────────────────────

def run_desktop_app() -> int:
    api_port = select_api_port()
    server_thread = FastAPIServerThread(api_port)
    server_thread.start()

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    window = MainWindow(api_port)
    window.show()
    return app.exec()
