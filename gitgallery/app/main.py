"""
GitGallery application entry point.

Starts the desktop app: ensures directories and logging, then shows
Connect GitHub if needed, then the dashboard.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import Qt

from gitgallery.app.config import ensure_directories, LOGS_DIR, LOG_FILENAME
from gitgallery.utils.logger import setup_logging, get_logger
from gitgallery.core.github_connector import GitHubConnector
from gitgallery.core.git_manager import is_git_installed
from gitgallery.ui.dashboard import Dashboard


def main() -> int:
    """Run the GitGallery desktop application."""
    ensure_directories()
    setup_logging(LOGS_DIR, LOG_FILENAME)

    logger = get_logger()
    logger.info("GitGallery starting")

    if not is_git_installed():
        # Show error in GUI if we have one, else stderr
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Git Required",
            "Git is not installed or not in PATH. Please install Git and try again.\n\nhttps://git-scm.com/downloads",
        )
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("GitGallery")
    app.setApplicationDisplayName("GitGallery")

    github = GitHubConnector()
    dashboard = Dashboard(github)

    window = QMainWindow()
    window.setCentralWidget(dashboard)
    window.setWindowTitle("GitGallery")
    window.setMinimumSize(900, 600)
    window.resize(1000, 700)

    window.show()

    # First-run: user must connect GitHub before using the app
    if not github.is_connected:
        from gitgallery.ui.connect_github_dialog import ConnectGitHubDialog
        dlg = ConnectGitHubDialog(github, window)
        if dlg.exec() != ConnectGitHubDialog.DialogCode.Accepted:
            logger.info("User cancelled GitHub connection")
        # After connect, prompt for repo selection
        elif not dashboard.ensure_github_and_repo():
            logger.info("User cancelled repo selection")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
