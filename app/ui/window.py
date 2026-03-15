from __future__ import annotations

import sys
import threading

import uvicorn
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.api.server import create_app
from app.config import API_HOST, APP_NAME
from app.models import CommandResponse
from app.runtime import select_api_port
from app.services import dispatcher, parser, permission_service


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


class MainWindow(QMainWindow):
    def __init__(self, api_port: int) -> None:
        super().__init__()
        self.api_port = api_port
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

        input_row = QHBoxLayout()
        input_row.addWidget(self.input)
        input_row.addWidget(submit_button)

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
