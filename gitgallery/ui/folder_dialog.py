"""
Folder selection / creation dialog.

Used when uploading: choose existing folder or create a new one.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt

from gitgallery.utils.helpers import is_safe_folder_name
from gitgallery.ui.theme import apply_dark_theme


class FolderDialog(QDialog):
    """
    Dialog to pick an existing folder or create a new one.
    Returns the chosen folder name (string) or None if cancelled.
    """

    def __init__(
        self,
        existing_folders: List[str],
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._existing = existing_folders
        self._chosen: Optional[str] = None
        self.setWindowTitle("Choose Folder")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self) -> None:
        apply_dark_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Choose Folder")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Select an existing folder or create a new one.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("muted", True)
        layout.addWidget(subtitle)

        self._list = QListWidget()
        self._list.setMinimumHeight(180)
        for name in self._existing:
            self._list.addItem(name)
        self._list.itemDoubleClicked.connect(self._on_select_item)
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        self._select_btn = QPushButton("Use Selected")
        self._select_btn.setProperty("accent", True)
        self._select_btn.style().unpolish(self._select_btn)
        self._select_btn.style().polish(self._select_btn)
        self._select_btn.clicked.connect(self._on_select_clicked)
        btn_layout.addWidget(self._select_btn)

        create_btn = QPushButton("Create New Folder")
        create_btn.clicked.connect(self._create_new)
        btn_layout.addWidget(create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_select_item(self, item: QListWidgetItem) -> None:
        self._chosen = item.text()
        self.accept()

    def _on_select_clicked(self) -> None:
        item = self._list.currentItem()
        if not item:
            QMessageBox.information(self, "Select", "Please select a folder.")
            return
        self._chosen = item.text()
        self.accept()

    def _create_new(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "New Folder",
            "Folder name:",
        )
        if not ok or not name or not name.strip():
            return
        name = name.strip()
        if not is_safe_folder_name(name):
            QMessageBox.warning(
                self,
                "Invalid",
                "Folder name contains invalid characters or is too long.",
            )
            return
        self._chosen = name
        self.accept()

    def chosen_folder(self) -> Optional[str]:
        """Return the selected or newly created folder name, or None."""
        return self._chosen
