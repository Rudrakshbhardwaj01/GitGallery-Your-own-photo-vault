"""Gallery view with responsive thumbnails, filtering, and metadata panel."""

from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from PIL import Image
from PySide6.QtCore import QEvent, QFileInfo, QMimeData, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from gitgallery.app.config import ALLOWED_IMAGE_EXTENSIONS
from gitgallery.models.photo import Photo


DEFAULT_THUMB_SIZE = 200
MIN_THUMB_SIZE = 120
MAX_THUMB_SIZE = 300


class ClickableLabel(QLabel):
    """Label that emits click signal when pressed."""

    clicked = Signal()

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class ThumbnailWidget(QFrame):
    """Single thumbnail card with checkbox and filename."""

    selection_changed = Signal(object, bool)

    def __init__(
        self,
        photo: Photo,
        thumb_size: int,
        on_open: Optional[Callable[[Photo], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.photo = photo
        self._thumb_size = thumb_size
        self._on_open = on_open

        self.setObjectName("thumbCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._check = QCheckBox()
        self._check.stateChanged.connect(self._on_check_changed)
        layout.addWidget(
            self._check,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )

        self._label = ClickableLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: #0b0f14; border: 1px solid #1f2933; border-radius: 6px;")
        self._label.clicked.connect(self._open_image)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_label = QLabel(photo.name)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)

        self.set_thumb_size(thumb_size)
        self._update_selected_style()

    def _load_thumb(self) -> None:
        source = self.photo.thumbnail_path if self.photo.thumbnail_path and self.photo.thumbnail_path.exists() else self.photo.file_path
        if not source.exists():
            self._label.setText("(missing)")
            self._label.setPixmap(QPixmap())
            return
        pix = QPixmap(str(source))
        if pix.isNull():
            self._label.setText("(?)")
            self._label.setPixmap(QPixmap())
            return
        self._label.setText("")
        scaled = pix.scaled(
            self._thumb_size,
            self._thumb_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)

    def set_thumb_size(self, size: int) -> None:
        self._thumb_size = size
        self._label.setFixedSize(size, size)
        self._name_label.setMaximumWidth(size + 10)
        self._load_thumb()

    def is_checked(self) -> bool:
        return self._check.isChecked()

    def set_checked(self, checked: bool) -> None:
        self._check.setChecked(checked)

    def _open_image(self) -> None:
        if self._on_open:
            self._on_open(self.photo)

    def _on_check_changed(self, state: int) -> None:
        checked = state == int(Qt.CheckState.Checked)
        self._update_selected_style()
        self.selection_changed.emit(self.photo, checked)

    def _update_selected_style(self) -> None:
        self.setProperty("selected", self._check.isChecked())
        self.style().unpolish(self)
        self.style().polish(self)


class GalleryView(QWidget):
    """Main gallery with responsive grid, filters, and selection actions."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._photos: List[Photo] = []
        self._filtered_photos: List[Photo] = []
        self._available_folders: List[str] = []
        self._thumb_widgets: List[ThumbnailWidget] = []
        self._selected_paths: Set[str] = set()
        self._thumb_size = DEFAULT_THUMB_SIZE

        self._on_open: Optional[Callable[[Photo], None]] = None
        self._on_download: Optional[Callable[..., None]] = None
        self._on_delete: Optional[Callable[[List[Photo]], None]] = None
        self._on_files_dropped: Optional[Callable[[List[Path]], None]] = None
        self._on_slideshow: Optional[Callable[[List[Photo], int], None]] = None

        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(10)

        self._sidebar = QFrame()
        self._sidebar.setObjectName("card")
        self._sidebar.setFixedWidth(270)
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        folders_title = QLabel("Folders")
        folders_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        sidebar_layout.addWidget(folders_title)

        self._folder_list = QListWidget()
        self._folder_list.currentItemChanged.connect(self._on_filters_changed)
        sidebar_layout.addWidget(self._folder_list, 1)

        info_title = QLabel("Repository Info")
        info_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        sidebar_layout.addWidget(info_title)

        self._total_photos_label = QLabel("Total Photos: 0")
        self._total_folders_label = QLabel("Total Folders: 0")
        self._last_sync_label = QLabel("Last Sync: Never")
        self._last_sync_label.setProperty("muted", True)
        sidebar_layout.addWidget(self._total_photos_label)
        sidebar_layout.addWidget(self._total_folders_label)
        sidebar_layout.addWidget(self._last_sync_label)

        sidebar_layout.addSpacing(8)
        meta_title = QLabel("Photo Info")
        meta_title.setStyleSheet("font-size: 14px; font-weight: 700;")
        sidebar_layout.addWidget(meta_title)

        self._meta_name = QLabel("Name: -")
        self._meta_resolution = QLabel("Resolution: -")
        self._meta_size = QLabel("Size: -")
        self._meta_modified = QLabel("Date Modified: -")
        sidebar_layout.addWidget(self._meta_name)
        sidebar_layout.addWidget(self._meta_resolution)
        sidebar_layout.addWidget(self._meta_size)
        sidebar_layout.addWidget(self._meta_modified)

        sidebar_layout.addStretch()
        root.addWidget(self._sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("Gallery")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch()
        self._count_label = QLabel("0 photos")
        self._count_label.setProperty("muted", True)
        header_row.addWidget(self._count_label)
        right_layout.addLayout(header_row)

        tools_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search photos...")
        self._search.textChanged.connect(self._on_filters_changed)
        tools_row.addWidget(self._search, 1)

        tools_row.addWidget(QLabel("Thumbnail Size"))
        self._thumb_slider = QSlider(Qt.Orientation.Horizontal)
        self._thumb_slider.setRange(MIN_THUMB_SIZE, MAX_THUMB_SIZE)
        self._thumb_slider.setValue(self._thumb_size)
        self._thumb_slider.setFixedWidth(150)
        self._thumb_slider.valueChanged.connect(self._on_thumb_size_changed)
        tools_row.addWidget(self._thumb_slider)
        right_layout.addLayout(tools_row)

        action_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._toggle_select_all)
        action_row.addWidget(self._select_all_btn)

        self._download_btn = QPushButton("Download")
        self._download_btn.clicked.connect(self._download_selected)
        action_row.addWidget(self._download_btn)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self._delete_btn)

        self._slideshow_btn = QPushButton("Start Slideshow")
        self._slideshow_btn.clicked.connect(self._start_slideshow)
        action_row.addWidget(self._slideshow_btn)

        action_row.addStretch()
        right_layout.addLayout(action_row)

        self._empty_label = QLabel("No photos yet. Upload images to populate the gallery.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setProperty("muted", True)
        right_layout.addWidget(self._empty_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._scroll.verticalScrollBar().setSingleStep(24)
        self._scroll.horizontalScrollBar().setSingleStep(24)

        self._scroll_content = QWidget()
        self._scroll_content.installEventFilter(self)
        self._grid = QGridLayout(self._scroll_content)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(12)
        self._scroll.setWidget(self._scroll_content)
        right_layout.addWidget(self._scroll, 1)
        root.addWidget(right_panel, 1)

        self._scroll.setVisible(False)

        self.setStyleSheet(
            self.styleSheet()
            + """
        QFrame#thumbCard {
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 8px;
            background: #0d1117;
        }
        QFrame#thumbCard[selected="true"] {
            border: 1px solid #8b5cf6;
            background: #111827;
        }
        QFrame#thumbCard:hover {
            border: 1px solid #475569;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
        }
        QCheckBox::indicator:unchecked {
            border: 1px solid #4b5d71;
            background: #0f141b;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            border: 1px solid #8b5cf6;
            background: #8b5cf6;
            border-radius: 3px;
        }
        """
        )

    def set_photos(self, photos: List[Photo]) -> None:
        self._photos = list(photos)
        available = {str(p.file_path) for p in self._photos}
        self._selected_paths = {p for p in self._selected_paths if p in available}
        self._refresh_folder_sidebar()
        self._apply_filters()

    def set_storage_info(self, total_photos: int, total_folders: int, last_sync: str) -> None:
        self._total_photos_label.setText(f"Total Photos: {total_photos}")
        self._total_folders_label.setText(f"Total Folders: {total_folders}")
        self._last_sync_label.setText(f"Last Sync: {last_sync}")

    def set_folders(self, folders: List[str]) -> None:
        self._available_folders = sorted({f for f in folders if f})
        self._refresh_folder_sidebar()
        self._apply_filters()

    def set_on_open(self, callback: Callable[[Photo], None]) -> None:
        self._on_open = callback

    def set_on_download(self, callback: Callable[..., None]) -> None:
        self._on_download = callback

    def set_on_delete(self, callback: Callable[[List[Photo]], None]) -> None:
        self._on_delete = callback

    def set_on_files_dropped(self, callback: Callable[[List[Path]], None]) -> None:
        self._on_files_dropped = callback

    def set_on_slideshow(self, callback: Callable[[List[Photo], int], None]) -> None:
        self._on_slideshow = callback

    def focus_folder_sidebar(self) -> None:
        self._folder_list.setFocus(Qt.FocusReason.OtherFocusReason)

    def get_viewer_context(self, start_photo: Photo) -> Tuple[List[Photo], int]:
        photos = list(self._filtered_photos) if self._filtered_photos else list(self._photos)
        if not photos:
            return [], 0
        for idx, photo in enumerate(photos):
            if photo.file_path == start_photo.file_path:
                return photos, idx
        return photos, 0

    def dragEnterEvent(self, event: object) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: object) -> None:
        self._handle_drop(event.mimeData())
        event.acceptProposedAction()

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if obj is self._scroll_content:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                return True
            if event.type() == QEvent.Type.Drop:
                self._handle_drop(event.mimeData())
                event.acceptProposedAction()
                return True
        return super().eventFilter(obj, event)

    def _handle_drop(self, mime_data: QMimeData) -> None:
        paths: List[Path] = []
        for url in mime_data.urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                paths.append(path)
        if paths and self._on_files_dropped:
            self._on_files_dropped(paths)

    def _folder_name(self, photo: Photo) -> str:
        rel = Path(photo.folder_relative_path)
        if len(rel.parts) > 1:
            return rel.parts[0]
        return "(root)"

    def _refresh_folder_sidebar(self) -> None:
        selected_folder = self._current_folder_filter()
        self._folder_list.blockSignals(True)
        self._folder_list.clear()

        all_item = QListWidgetItem("All Folders")
        all_item.setData(Qt.ItemDataRole.UserRole, "")
        self._folder_list.addItem(all_item)

        derived_folders = {self._folder_name(p) for p in self._photos}
        folders = sorted(set(self._available_folders) | derived_folders)
        for folder in folders:
            item = QListWidgetItem(folder)
            item.setData(Qt.ItemDataRole.UserRole, folder)
            self._folder_list.addItem(item)

        target = "" if selected_folder is None else selected_folder
        for i in range(self._folder_list.count()):
            item = self._folder_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == target:
                self._folder_list.setCurrentRow(i)
                break
        if self._folder_list.currentRow() < 0 and self._folder_list.count() > 0:
            self._folder_list.setCurrentRow(0)

        self._folder_list.blockSignals(False)

    def _current_folder_filter(self) -> Optional[str]:
        item = self._folder_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        if value == "":
            return None
        return str(value)

    def _on_filters_changed(self, *args: object) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        query = self._search.text().strip().lower()
        folder = self._current_folder_filter()

        self._filtered_photos = []
        for photo in self._photos:
            photo_folder = self._folder_name(photo)
            if folder and photo_folder != folder:
                continue
            if query:
                haystack = f"{photo.name} {photo_folder}".lower()
                if query not in haystack:
                    continue
            self._filtered_photos.append(photo)

        self._count_label.setText(f"{len(self._filtered_photos)} photos")
        self._refresh_grid()

    def _refresh_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._thumb_widgets.clear()
        self._empty_label.setVisible(not self._filtered_photos)
        self._scroll.setVisible(bool(self._filtered_photos))

        cols = max(1, self._scroll.viewport().width() // (self._thumb_size + 64))
        for i, photo in enumerate(self._filtered_photos):
            card = ThumbnailWidget(photo, self._thumb_size, self._on_open, self)
            card.selection_changed.connect(self._on_thumb_selection_changed)
            card.set_checked(str(photo.file_path) in self._selected_paths)
            self._thumb_widgets.append(card)
            row, col = divmod(i, cols)
            self._grid.addWidget(card, row, col)

        self._update_select_all_button()
        self._update_metadata_from_selection()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if not self._thumb_widgets:
            return
        cols = max(1, self._scroll.viewport().width() // (self._thumb_size + 64))
        for i, card in enumerate(self._thumb_widgets):
            row, col = divmod(i, cols)
            self._grid.addWidget(card, row, col)

    def _on_thumb_size_changed(self, value: int) -> None:
        self._thumb_size = value
        for card in self._thumb_widgets:
            card.set_thumb_size(value)
        self._refresh_grid()

    def _selected_photos(self) -> List[Photo]:
        selected = []
        selected_set = set(self._selected_paths)
        for photo in self._photos:
            if str(photo.file_path) in selected_set:
                selected.append(photo)
        return selected

    def _on_thumb_selection_changed(self, photo: Photo, checked: bool) -> None:
        key = str(photo.file_path)
        if checked:
            self._selected_paths.add(key)
        else:
            self._selected_paths.discard(key)
        self._update_select_all_button()
        self._update_metadata_from_selection()

    def _update_select_all_button(self) -> None:
        if not self._thumb_widgets:
            self._select_all_btn.setText("Select All")
            return
        all_selected = all(card.is_checked() for card in self._thumb_widgets)
        self._select_all_btn.setText("Clear Selection" if all_selected else "Select All")

    def _toggle_select_all(self) -> None:
        if not self._thumb_widgets:
            return
        all_selected = all(card.is_checked() for card in self._thumb_widgets)
        for card in self._thumb_widgets:
            card.set_checked(not all_selected)

    def _update_metadata_from_selection(self) -> None:
        selected = self._selected_photos()
        if not selected:
            self._meta_name.setText("Name: -")
            self._meta_resolution.setText("Resolution: -")
            self._meta_size.setText("Size: -")
            self._meta_modified.setText("Date Modified: -")
            return

        photo = selected[0]
        info = QFileInfo(str(photo.file_path))
        resolution = "Unknown"
        try:
            with Image.open(photo.file_path) as img:
                resolution = f"{img.width} x {img.height}"
        except Exception:
            resolution = "Unknown"

        self._meta_name.setText(f"Name: {photo.name}")
        self._meta_resolution.setText(f"Resolution: {resolution}")
        self._meta_size.setText(f"Size: {self._format_bytes(info.size())}")
        self._meta_modified.setText(f"Date Modified: {info.lastModified().toString(Qt.DateFormat.DefaultLocaleLongDate)}")

    def _format_bytes(self, size: int) -> str:
        value = float(size)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if value < 1024.0 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{int(size)} B"

    def _download_selected(self) -> None:
        selected = self._selected_photos()
        if not selected:
            QMessageBox.information(self, "Download", "Select one or more images to download.")
            return
        if not self._on_download:
            return

        if len(selected) == 1:
            self._on_download(selected[0], None)
            return

        dir_path = QFileDialog.getExistingDirectory(self, "Save images to folder")
        if not dir_path:
            return
        for photo in selected:
            self._on_download(photo, Path(dir_path))

    def _delete_selected(self) -> None:
        selected = self._selected_photos()
        if not selected:
            QMessageBox.information(self, "Delete", "Select images to delete.")
            return
        if QMessageBox.question(
            self,
            "Delete",
            f"Delete {len(selected)} image(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        if self._on_delete:
            self._on_delete(selected)

    def _start_slideshow(self) -> None:
        if not self._on_slideshow:
            return
        photos = list(self._filtered_photos) if self._filtered_photos else list(self._photos)
        if not photos:
            QMessageBox.information(self, "Slideshow", "No images to show.")
            return

        selected = self._selected_photos()
        start_index = 0
        if selected:
            selected_key = str(selected[0].file_path)
            for idx, photo in enumerate(photos):
                if str(photo.file_path) == selected_key:
                    start_index = idx
                    break

        self._on_slideshow(photos, start_index)
