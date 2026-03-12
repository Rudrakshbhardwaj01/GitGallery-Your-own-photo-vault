"""
How-To Guide page.

Explains: Create GitHub account, Install Git, Generate SSH key,
Add SSH key to GitHub, Connect GitHub to GitGallery.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class HowToPage(QWidget):
    """Static how-to guide accessible from the dashboard sidebar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("How-To Guide")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)

        steps = [
            (
                "Step 1: Create a GitHub account",
                "If you don't have one, go to https://github.com and sign up.",
            ),
            (
                "Step 2: Install Git",
                "Install Git on your computer. Download from https://git-scm.com/downloads",
            ),
            (
                "Step 3: Generate an SSH key",
                "Open a terminal and run:\n\n"
                "ssh-keygen -t ed25519 -C \"your_email@example.com\"\n\n"
                "Press Enter to accept the default file location, and optionally set a passphrase.",
            ),
            (
                "Step 4: Add your SSH key to GitHub",
                "Copy your public key (for example from ~/.ssh/id_ed25519.pub on Linux/Mac, "
                "or %USERPROFILE%\\.ssh\\id_ed25519.pub on Windows), then go to "
                "GitHub -> Settings -> SSH and GPG keys -> New SSH key, and paste it.",
            ),
            (
                "Step 5: Connect GitHub to GitGallery",
                "In GitGallery, click 'Connect GitHub Account' and complete authorization "
                "in your browser. Then select or create a repository to store your photos.",
            ),
        ]
        for heading, body in steps:
            frame = QFrame()
            frame.setObjectName("card")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(14, 12, 14, 12)
            fl.setSpacing(6)

            h = QLabel(heading)
            h.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            fl.addWidget(h)

            body_label = QLabel(body)
            body_label.setWordWrap(True)
            body_label.setProperty("muted", True)
            fl.addWidget(body_label)

            content_layout.addWidget(frame)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
