"""
Upload images dialog.

Lets user pick image files, then choose target folder (existing or new).
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Qt

from gitgallery.app.config import ALLOWED_IMAGE_EXTENSIONS
from gitgallery.ui.theme import apply_dark_theme


class UploadDialog(QDialog):
    """
    Select one or more image files to upload.
    Returns list of selected file paths.
    """

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self._paths: List[Path] = []
        self.setWindowTitle("Upload Images")
        self.setMinimumSize(520, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        apply_dark_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Upload Images")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Choose one or more image files to add to your gallery.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("muted", True)
        layout.addWidget(subtitle)

        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        layout.addWidget(self._list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.setProperty("accent", True)
        add_btn.style().unpolish(add_btn)
        add_btn.style().polish(add_btn)
        add_btn.clicked.connect(self._add_files)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        ok_btn = QPushButton("Upload")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout2 = QHBoxLayout()
        btn_layout2.addWidget(ok_btn)
        btn_layout2.addWidget(cancel_btn)
        layout.addLayout(btn_layout2)

    def _add_files(self) -> None:
        exts = " ".join(f"*{e}" for e in ALLOWED_IMAGE_EXTENSIONS)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            f"Images ({exts});;All files (*)",
        )
        for p in paths:
            path = Path(p)
            if path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                if path not in self._paths:
                    self._paths.append(path)
                    self._list.addItem(path.name)

    def _remove_selected(self) -> None:
        row = self._list.currentRow()
        if row >= 0 and row < len(self._paths):
            self._paths.pop(row)
            self._list.takeItem(row)

    def selected_paths(self) -> List[Path]:
        """Return list of selected file paths."""
        return list(self._paths)
