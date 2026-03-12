"""In-app image viewer dialog with zoom, navigation, and slideshow."""

from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gitgallery.models.photo import Photo
from gitgallery.ui.theme import apply_dark_theme


class ImageViewerDialog(QDialog):
    """Image preview dialog with next/previous, zoom, and fullscreen support."""

    def __init__(
        self,
        photos: List[Photo],
        start_index: int = 0,
        on_download: Optional[Callable[[Photo], None]] = None,
        on_delete: Optional[Callable[[Photo], None]] = None,
        slideshow: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._photos = list(photos)
        self._index = max(0, min(start_index, len(self._photos) - 1)) if self._photos else 0
        self._on_download = on_download
        self._on_delete = on_delete
        self._zoom_factor = 1.0
        self._base_pixmap = QPixmap()
        self._slideshow = slideshow
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.setInterval(3000)
        self._slideshow_timer.timeout.connect(self._next_photo)

        self.setWindowTitle("Image Viewer")
        self.resize(1024, 720)
        self._build_ui()
        self._show_current_photo()

        if self._slideshow:
            self.showFullScreen()
            self._slideshow_timer.start()

    def _build_ui(self) -> None:
        apply_dark_theme(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top_row = QHBoxLayout()
        self._prev_btn = QPushButton("<-")
        self._prev_btn.clicked.connect(self._prev_photo)
        top_row.addWidget(self._prev_btn)

        self._title = QLabel("No image")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-size: 14px; font-weight: 600;")
        top_row.addWidget(self._title, 1)

        self._next_btn = QPushButton("->")
        self._next_btn.clicked.connect(self._next_photo)
        top_row.addWidget(self._next_btn)
        root.addLayout(top_row)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.verticalScrollBar().setSingleStep(24)
        self._scroll.horizontalScrollBar().setSingleStep(24)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image_label.setText("No image")
        self._scroll.setWidget(self._image_label)
        root.addWidget(self._scroll, 1)

        controls = QHBoxLayout()
        zoom_in_btn = QPushButton("Zoom +")
        zoom_in_btn.clicked.connect(self._zoom_in)
        controls.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom -")
        zoom_out_btn.clicked.connect(self._zoom_out)
        controls.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self._fit_to_window)
        controls.addWidget(fit_btn)

        fullscreen_btn = QPushButton("Fullscreen")
        fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        controls.addWidget(fullscreen_btn)

        controls.addStretch()

        download_btn = QPushButton("Download")
        download_btn.clicked.connect(self._download_current)
        controls.addWidget(download_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_current)
        controls.addWidget(delete_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        controls.addWidget(close_btn)

        root.addLayout(controls)

    def _current_photo(self) -> Optional[Photo]:
        if not self._photos:
            return None
        return self._photos[self._index]

    def _show_current_photo(self) -> None:
        photo = self._current_photo()
        if photo is None:
            self._title.setText("No image")
            self._image_label.setText("No image")
            self._image_label.setPixmap(QPixmap())
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        self._title.setText(photo.name)
        pix = QPixmap(str(photo.file_path))
        if pix.isNull():
            self._base_pixmap = QPixmap()
            self._image_label.setText("Unable to load image")
            self._image_label.setPixmap(QPixmap())
            return

        self._base_pixmap = pix
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        if self._base_pixmap.isNull():
            return
        target = self._base_pixmap.scaled(
            int(self._base_pixmap.width() * self._zoom_factor),
            int(self._base_pixmap.height() * self._zoom_factor),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(target)
        self._image_label.adjustSize()

    def _fit_to_window(self) -> None:
        self._zoom_factor = 1.0
        self._apply_zoom()

    def _zoom_in(self) -> None:
        self._zoom_factor = min(5.0, self._zoom_factor + 0.15)
        self._apply_zoom()

    def _zoom_out(self) -> None:
        self._zoom_factor = max(0.1, self._zoom_factor - 0.15)
        self._apply_zoom()

    def _prev_photo(self) -> None:
        if not self._photos:
            return
        self._index = (self._index - 1) % len(self._photos)
        self._zoom_factor = 1.0
        self._show_current_photo()

    def _next_photo(self) -> None:
        if not self._photos:
            return
        self._index = (self._index + 1) % len(self._photos)
        self._zoom_factor = 1.0
        self._show_current_photo()

    def _download_current(self) -> None:
        photo = self._current_photo()
        if photo is None or self._on_download is None:
            return
        self._on_download(photo)

    def _delete_current(self) -> None:
        photo = self._current_photo()
        if photo is None or self._on_delete is None:
            return
        self._on_delete(photo)
        self.close()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._prev_photo()
            return
        if event.key() == Qt.Key.Key_Right:
            self._next_photo()
            return
        if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._zoom_in()
            return
        if event.key() == Qt.Key.Key_Minus:
            self._zoom_out()
            return
        if event.key() == Qt.Key.Key_F:
            self._toggle_fullscreen()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                if self._slideshow:
                    self.close()
            else:
                self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: object) -> None:
        self._slideshow_timer.stop()
        super().closeEvent(event)
