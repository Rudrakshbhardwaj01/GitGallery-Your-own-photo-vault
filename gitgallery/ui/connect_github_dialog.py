"""
Connect GitHub Account dialog.

First-run mandatory screen: user must authenticate via GitHub OAuth
before using GitGallery. Opens browser for auth and runs a local callback server.
"""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QFrame,
)
from PySide6.QtGui import QFont

from gitgallery.core.github_connector import (
    GitHubConnector,
    REDIRECT_URI,
    LOCAL_CALLBACK_PORT,
)
from gitgallery.utils.logger import get_logger
from gitgallery.ui.theme import apply_dark_theme

logger = get_logger()


class _CallbackHandler(BaseHTTPRequestHandler):
    """One-shot handler that captures ?code= and sets it on the server."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            qs = parse_qs(parsed.query)
            code_list = qs.get("code")
            if code_list:
                code = code_list[0]
                if hasattr(self.server, "on_code"):
                    self.server.on_code(code)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GitGallery Authorization</title>
  <style>
    :root {
      color-scheme: dark;
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: radial-gradient(circle at top, #131a23 0%, #0d1117 45%, #0d1117 100%);
      color: #e6edf3;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    }
    .card {
      width: min(92vw, 520px);
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 14px;
      padding: 30px 24px;
      text-align: center;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
    }
    .brand {
      margin: 0;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }
    .status {
      margin: 10px 0 6px;
      font-size: 21px;
      font-weight: 700;
      color: #3fb950;
    }
    .subtitle {
      margin: 0;
      color: #9aa4b2;
      line-height: 1.55;
      font-size: 14px;
    }
    .note {
      margin-top: 16px;
      display: inline-block;
      background: #0f141b;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 8px 12px;
      color: #c9d1d9;
      font-size: 12px;
    }
  </style>
</head>
<body>
  <main class="card">
    <h1 class="brand">GitGallery</h1>
    <div class="status">Authorization Successful</div>
    <p class="subtitle">Your GitHub account is now connected to GitGallery. You can safely close this tab and return to the desktop app.</p>
    <div class="note">Return to GitGallery to continue.</div>
  </main>
</body>
</html>
"""
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        logger.debug("OAuth callback: %s", args)


def _run_callback_server(port: int, on_code: Callable[[str], None]) -> None:
    """Run a single-request HTTP server to capture OAuth code."""
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.on_code = on_code
    server.handle_request()


class OAuthSignals(QObject):
    """Signals for OAuth result (thread-safe)."""
    code_received = Signal(str)
    error = Signal(str)


class ConnectGitHubDialog(QDialog):
    """
    Dialog shown on first run: connect GitHub via OAuth.
    On success, emits connected() and provides the GitHubConnector with token set.
    """

    def __init__(
        self,
        github: GitHubConnector,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._github = github
        self._signals = OAuthSignals()
        self._signals.code_received.connect(self._on_code_received)
        self._signals.error.connect(self._on_oauth_error)

        self.setWindowTitle("Connect GitHub Account")
        self.setMinimumWidth(520)
        self.setMinimumHeight(300)

        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header
        title = QLabel("Connect Your GitHub Account")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "GitGallery securely stores your photos inside your own GitHub repositories."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Card container
        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        info = QLabel(
            "To begin using GitGallery, you must authorize access to your GitHub account.\n\n"
            "After clicking the button below, your browser will open where you can approve the connection."
        )
        info.setWordWrap(True)

        card_layout.addWidget(info)

        self._status = QLabel(
            "Click the button below to open GitHub and authorize GitGallery."
        )
        self._status.setWordWrap(True)
        self._status.setObjectName("statusLabel")

        card_layout.addWidget(self._status)

        main_layout.addWidget(card)

        # Buttons
        btn_layout = QHBoxLayout()

        self._connect_btn = QPushButton("Connect GitHub")
        self._connect_btn.setProperty("accent", True)
        self._connect_btn.style().unpolish(self._connect_btn)
        self._connect_btn.style().polish(self._connect_btn)
        self._connect_btn.setMinimumHeight(40)
        self._connect_btn.clicked.connect(self._start_oauth)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setMinimumHeight(40)
        self._cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self._connect_btn)
        btn_layout.addWidget(self._cancel_btn)

        main_layout.addLayout(btn_layout)

    def _apply_styles(self) -> None:
        apply_dark_theme(self)
        self.setStyleSheet(
            self.styleSheet()
            + """
        QFrame {
            background-color: #11161d;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #1f2933;
        }

        #statusLabel {
            color: #9aa4b2;
        }
        """
        )

    def _start_oauth(self) -> None:
        self._connect_btn.setEnabled(False)
        self._status.setText(
            "Opening browser... Complete authorization in the browser, then return here."
        )

        url = self._github.get_authorization_url()

        import webbrowser
        webbrowser.open(url)

        def run_server() -> None:
            try:
                code_holder: list[str] = []

                def on_code(c: str) -> None:
                    code_holder.append(c)
                    self._signals.code_received.emit(c)

                _run_callback_server(LOCAL_CALLBACK_PORT, on_code)

                if not code_holder:
                    self._signals.error.emit(
                        "No authorization code received. Did you approve the app?"
                    )

            except Exception as e:
                self._signals.error.emit(str(e))

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

    def _on_code_received(self, code: str) -> None:
        try:
            self._github.exchange_code_for_token(code)
            self._status.setText("Connected successfully.")
            self.accept()

        except Exception as e:
            logger.exception("Token exchange failed")
            self._signals.error.emit(str(e))

    def _on_oauth_error(self, message: str) -> None:
        self._connect_btn.setEnabled(True)
        self._status.setText("Connection failed. Try again.")
        QMessageBox.warning(self, "GitHub Connection", message)
