"""Shared styling for GitGallery UI widgets."""

from PySide6.QtWidgets import QWidget

APP_STYLESHEET = """
QWidget {
    background-color: #0b0f14;
    color: #e6edf3;
    font-family: "Segoe UI";
    font-size: 13px;
}

QLabel[muted="true"] {
    color: #9aa4b2;
}

QFrame#card {
    background-color: #11161d;
    border: 1px solid #1f2933;
    border-radius: 12px;
}

QPushButton {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e6edf3;
}

QPushButton:hover {
    background-color: #1c2531;
    border: 1px solid #3a4755;
}

QPushButton:pressed {
    background-color: #121921;
}

QPushButton:disabled {
    color: #7a8696;
    background-color: #11161d;
    border: 1px solid #273240;
}

QPushButton[accent="true"] {
    background-color: #8b5cf6;
    border: 1px solid #8b5cf6;
    color: #ffffff;
    font-weight: 600;
}

QPushButton[accent="true"]:hover {
    background-color: #7c4deb;
    border: 1px solid #7c4deb;
}

QListWidget, QScrollArea {
    background-color: #0f141b;
    border: 1px solid #1f2933;
    border-radius: 10px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 6px;
    margin: 2px 4px;
}

QListWidget::item:selected {
    background-color: #1f2933;
    border: 1px solid #304155;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0f141b;
    border: 1px solid #253241;
    border-radius: 8px;
    padding: 6px 8px;
}

QProgressBar {
    background-color: #11161d;
    border: 1px solid #1f2933;
    border-radius: 4px;
    text-align: center;
    min-height: 6px;
    max-height: 6px;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 4px;
}

QScrollBar:vertical {
    background: #0f141b;
    width: 10px;
    margin: 4px 0 4px 0;
    border: none;
}

QScrollBar::handle:vertical {
    background: #243142;
    min-height: 24px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #0f141b;
    height: 10px;
    margin: 0 4px 0 4px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: #243142;
    min-width: 24px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


def apply_dark_theme(widget: QWidget) -> None:
    """Apply shared dark styling to a top-level widget/dialog."""
    widget.setStyleSheet(APP_STYLESHEET)
