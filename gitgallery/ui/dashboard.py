"""
Main dashboard: sidebar navigation and main panel.

Sidebar: Gallery, Upload, Folders, Repositories, Sync, How-To Guide.
Main panel: gallery view or other pages.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QLabel,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QProgressBar,
)
from PySide6.QtGui import QFont
from gitgallery.ui.theme import apply_dark_theme

from gitgallery.core.github_connector import GitHubConnector
from gitgallery.core.repo_manager import get_physical_repos_for_folder
from gitgallery.core.file_manager import (
    list_folders_across_repos,
    list_photos_from_gallery_index,
    delete_photos,
)
from gitgallery.core.repo_manager import gallery_index_remove
from gitgallery.core import git_manager
from gitgallery.models.photo import Photo
from gitgallery.utils.logger import get_logger

from gitgallery.ui.connect_github_dialog import ConnectGitHubDialog
from gitgallery.ui.repo_selector import RepoSelectorDialog
from gitgallery.ui.upload_dialog import UploadDialog
from gitgallery.ui.folder_dialog import FolderDialog
from gitgallery.ui.gallery_view import GalleryView
from gitgallery.ui.howto_page import HowToPage
from gitgallery.ui.image_viewer_dialog import ImageViewerDialog
from gitgallery.workers.upload_worker import UploadWorker
from gitgallery.workers.git_worker import GitWorker

logger = get_logger()


class Dashboard(QWidget):
    """
    Main application window content: sidebar + stacked main panel.
    """

    def __init__(
        self,
        github: GitHubConnector,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._github = github
        self._current_logical_folders: List[str] = []
        self._current_repo_paths: List[Path] = []
        self._stack = QStackedWidget()
        self._gallery_view = GalleryView(self)
        self._howto = HowToPage(self)
        self._last_sync_text = "Never"
        self._temp_upload_dirs: List[Path] = []
        self._build_ui()
        self._gallery_view.set_on_open(self._open_full_image)
        self._gallery_view.set_on_download(self._download_photo)
        self._gallery_view.set_on_delete(self._delete_photos)
        self._gallery_view.set_on_files_dropped(self._on_gallery_files_dropped)
        self._gallery_view.set_on_slideshow(self._start_slideshow)

    def _build_ui(self) -> None:
        apply_dark_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self._connect_github_btn = QPushButton("Connect GitHub Account")
        self._connect_github_btn.clicked.connect(self._on_connect_github)
        top_bar.addWidget(self._connect_github_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        if self._github.is_connected:
            self._connect_github_btn.setEnabled(False)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        sidebar = QWidget()
        sidebar.setFixedWidth(232)
        sidebar.setObjectName("card")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 16, 14, 14)
        sl.setSpacing(8)

        title = QLabel("GitGallery")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        sl.addWidget(title)

        subtitle = QLabel("Your photo repo workspace")
        subtitle.setProperty("muted", True)
        sl.addWidget(subtitle)
        sl.addSpacing(10)

        self._nav_buttons: List[QPushButton] = []

        gallery_btn = QPushButton("Gallery")
        gallery_btn.setCheckable(True)
        gallery_btn.clicked.connect(lambda: self._show_gallery())
        sl.addWidget(gallery_btn)
        self._nav_buttons.append(gallery_btn)

        upload_btn = QPushButton("Upload")
        upload_btn.setCheckable(True)
        upload_btn.clicked.connect(self._on_upload)
        sl.addWidget(upload_btn)
        self._nav_buttons.append(upload_btn)

        folders_btn = QPushButton("Folders")
        folders_btn.setCheckable(True)
        folders_btn.clicked.connect(self._on_folders)
        sl.addWidget(folders_btn)
        self._nav_buttons.append(folders_btn)

        repos_btn = QPushButton("Repositories")
        repos_btn.setCheckable(True)
        repos_btn.clicked.connect(self._on_repositories)
        sl.addWidget(repos_btn)
        self._nav_buttons.append(repos_btn)

        sync_btn = QPushButton("Sync")
        sync_btn.setCheckable(True)
        sync_btn.clicked.connect(self._on_sync)
        sl.addWidget(sync_btn)
        self._nav_buttons.append(sync_btn)

        howto_btn = QPushButton("How-To Guide")
        howto_btn.setCheckable(True)
        howto_btn.clicked.connect(self._show_howto)
        sl.addWidget(howto_btn)
        self._nav_buttons.append(howto_btn)

        sl.addStretch()
        splitter.addWidget(sidebar)

        self._content_panel = QWidget()
        self._content_panel.setObjectName("card")
        content_layout = QVBoxLayout(self._content_panel)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        top_row = QHBoxLayout()
        header = QLabel("Workspace")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        top_row.addWidget(header)
        top_row.addStretch()
        content_layout.addLayout(top_row)

        self._stack.addWidget(self._gallery_view)
        self._stack.addWidget(self._howto)
        self._main_label = QLabel("Select a folder or repository to view photos.")
        self._main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_label.setProperty("muted", True)
        self._stack.addWidget(self._main_label)
        content_layout.addWidget(self._stack)
        splitter.addWidget(self._content_panel)
        splitter.setSizes([232, 768])

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        layout.addWidget(splitter)
        layout.addWidget(self._progress_bar)

        self.setStyleSheet(
            self.styleSheet()
            + """
        QPushButton {
            text-align: left;
        }
        QPushButton:checked {
            background-color: #1f2933;
            border: 1px solid #394c61;
        }
        """
        )
        self._upload_worker: Optional[UploadWorker] = None
        self._git_worker: Optional[GitWorker] = None
        self._sync_worker: Optional[GitWorker] = None
        self._set_active_nav(gallery_btn)

    def _set_active_nav(self, active_button: QPushButton) -> None:
        for button in self._nav_buttons:
            button.setChecked(button is active_button)

    def _show_howto(self) -> None:
        self._set_active_nav(self._nav_buttons[-1])
        self._stack.setCurrentWidget(self._howto)

    def _on_connect_github(self) -> None:
        dlg = ConnectGitHubDialog(self._github, self)
        dlg.exec()
        if self._github.is_connected:
            self._connect_github_btn.setEnabled(False)

    def _show_gallery(self) -> None:
        """Refresh and show gallery (from gallery index to avoid filesystem scan)."""
        self._set_active_nav(self._nav_buttons[0])
        if not self._current_repo_paths:
            self._stack.setCurrentWidget(self._main_label)
            return
        all_photos: List[Photo] = []
        for repo_path in self._current_repo_paths:
            all_photos.extend(list_photos_from_gallery_index(repo_path, repo_path.name))
        folders = list_folders_across_repos(self._current_repo_paths)
        folder_count = len(folders)
        self._gallery_view.set_photos(all_photos)
        self._gallery_view.set_folders([folder.name for folder in folders])
        self._gallery_view.set_storage_info(len(all_photos), folder_count, self._last_sync_text)
        self._stack.setCurrentWidget(self._gallery_view)

    def _on_upload(self) -> None:
        self._set_active_nav(self._nav_buttons[1])
        if not self._current_repo_paths:
            QMessageBox.information(
                self,
                "Upload",
                "Select a repository first (Repositories).",
            )
            return
        upload_dlg = UploadDialog(self)
        if upload_dlg.exec() != UploadDialog.DialogCode.Accepted:
            return
        paths = upload_dlg.selected_paths()
        if not paths:
            QMessageBox.information(self, "Upload", "No files selected.")
            return
        folder_name = self._prompt_upload_folder()
        if not folder_name:
            return
        resolved = self._resolve_duplicate_uploads(paths, folder_name)
        if not resolved:
            QMessageBox.information(self, "Upload", "No files selected for upload.")
            return
        self._start_upload_worker(resolved, folder_name)

    def _on_upload_progress(self, current: int, total: int) -> None:
        self._progress_bar.setValue(current)

    def _on_upload_finished(self, added: List[Path]) -> None:
        self._progress_bar.setVisible(False)
        self._cleanup_temp_upload_dirs()
        if not added:
            return
        repo_path = self._current_repo_paths[0]
        self._git_worker = GitWorker("add", repo_path=repo_path, paths=added)
        self._git_worker.finished_signal.connect(self._on_upload_git_commit)
        self._git_worker.error_signal.connect(self._on_upload_git_error)
        self._git_worker.start()

    def _on_upload_git_commit(self) -> None:
        repo_path = self._current_repo_paths[0]
        self._git_worker = GitWorker(
            "commit",
            repo_path=repo_path,
            message="Add image(s) to GitGallery",
        )
        self._git_worker.finished_signal.connect(self._on_upload_git_push)
        self._git_worker.error_signal.connect(self._on_upload_git_error)
        self._git_worker.start()

    def _on_upload_git_push(self) -> None:
        repo_path = self._current_repo_paths[0]
        self._git_worker = GitWorker("push", repo_path=repo_path)
        self._git_worker.finished_signal.connect(self._on_upload_done)
        self._git_worker.error_signal.connect(self._on_upload_git_error)
        self._git_worker.start()

    def _on_upload_done(self) -> None:
        self._cleanup_temp_upload_dirs()
        QMessageBox.information(self, "Upload", "Upload completed.")
        self._show_gallery()

    def _on_upload_error(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        self._cleanup_temp_upload_dirs()
        QMessageBox.warning(self, "Upload", message)

    def _on_gallery_files_dropped(self, paths: List[Path]) -> None:
        """Handle drag-and-drop of image files onto gallery: choose folder and upload."""
        if not self._current_repo_paths:
            QMessageBox.information(
                self,
                "Upload",
                "Select a repository first (Repositories).",
            )
            return
        folder_name = self._prompt_upload_folder()
        if not folder_name:
            return
        resolved = self._resolve_duplicate_uploads(paths, folder_name)
        if not resolved:
            return
        self._start_upload_worker(resolved, folder_name)

    def _on_upload_git_error(self, message: str) -> None:
        self._cleanup_temp_upload_dirs()
        QMessageBox.critical(self, "Upload", f"Git failed: {message}")
        self._show_gallery()

    def _on_folders(self) -> None:
        self._set_active_nav(self._nav_buttons[2])
        if not self._current_repo_paths:
            QMessageBox.information(self, "Folders", "Select a repository first.")
            return
        self._stack.setCurrentWidget(self._gallery_view)
        self._gallery_view.focus_folder_sidebar()

    def _on_repositories(self) -> None:
        self._set_active_nav(self._nav_buttons[3])
        dlg = RepoSelectorDialog(self._github, self)
        if dlg.exec() != RepoSelectorDialog.DialogCode.Accepted:
            return
        owner, name, local_path, is_new = dlg.result()
        if not local_path:
            return
        self._current_repo_paths = get_physical_repos_for_folder(name or "")
        if not self._current_repo_paths:
            self._current_repo_paths = [local_path]
        self._current_logical_folders = [name] if name else []
        self._show_gallery()

    def _on_sync(self) -> None:
        self._set_active_nav(self._nav_buttons[4])
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # indeterminate
        self._sync_worker = GitWorker("sync_all")
        self._sync_worker.finished_signal.connect(self._on_sync_finished)
        self._sync_worker.error_signal.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self) -> None:
        self._progress_bar.setVisible(False)
        self._last_sync_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        QMessageBox.information(self, "Sync", "Sync completed.")
        self._show_gallery()

    def _on_sync_error(self, message: str) -> None:
        self._progress_bar.setVisible(False)
        QMessageBox.critical(self, "Sync", message)

    def _open_full_image(self, photo: Photo) -> None:
        if not photo.file_path.exists():
            QMessageBox.warning(self, "Open", "File not found.")
            return
        photos, start_index = self._gallery_view.get_viewer_context(photo)
        viewer = ImageViewerDialog(
            photos,
            start_index=start_index,
            on_download=lambda p: self._download_photo(p, None),
            on_delete=lambda p: self._delete_photos([p]),
            parent=self,
        )
        viewer.exec()

    def _start_slideshow(self, photos: List[Photo], start_index: int) -> None:
        if not photos:
            QMessageBox.information(self, "Slideshow", "No images to show.")
            return
        viewer = ImageViewerDialog(
            photos,
            start_index=start_index,
            on_download=lambda p: self._download_photo(p, None),
            on_delete=lambda p: self._delete_photos([p]),
            slideshow=True,
            parent=self,
        )
        viewer.exec()

    def _download_photo(self, photo: Photo, dest_dir: Optional[Path] = None) -> None:
        if not photo.file_path.exists():
            QMessageBox.warning(self, "Download", "File not found.")
            return
        if dest_dir is None:
            dest_dir = QFileDialog.getExistingDirectory(self, "Save image to folder")
            if not dest_dir:
                return
            dest_dir = Path(dest_dir)
        dest_path = dest_dir / photo.name
        try:
            shutil.copy2(photo.file_path, dest_path)
            QMessageBox.information(self, "Download", f"Saved to {dest_path}")
        except Exception as e:
            QMessageBox.critical(self, "Download", str(e))

    def _delete_photos(self, photos: List[Photo]) -> None:
        if not photos:
            return
        # file_path is repo/folder/photo.jpg -> parent.parent is repo
        repo_path = photos[0].file_path.parent.parent
        repo_name = repo_path.name
        folder_name = photos[0].file_path.parent.name
        filenames = [p.name for p in photos]
        rel_paths = [Path(p.folder_relative_path) for p in photos]
        try:
            delete_photos(photos)
            gallery_index_remove(repo_name, folder_name, filenames)
            git_manager.rm(repo_path, rel_paths)
            git_manager.commit(repo_path, f"Remove {len(photos)} image(s)")
            git_manager.push(repo_path)
        except git_manager.GitError as e:
            QMessageBox.critical(self, "Delete", str(e))
            return
        QMessageBox.information(self, "Delete", f"Deleted {len(photos)} image(s).")
        self._show_gallery()

    def _prompt_upload_folder(self) -> Optional[str]:
        folders = list_folders_across_repos(self._current_repo_paths)
        folder_names = [f.name for f in folders]
        folder_dlg = FolderDialog(folder_names, self)
        if folder_dlg.exec() != FolderDialog.DialogCode.Accepted:
            return None
        return folder_dlg.chosen_folder()

    def _start_upload_worker(self, paths: List[Path], folder_name: str) -> None:
        repo_path = self._current_repo_paths[0]
        repo_name = repo_path.name
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(paths))
        self._progress_bar.setValue(0)
        self._upload_worker = UploadWorker(repo_path, repo_name, folder_name, paths)
        self._upload_worker.progress_signal.connect(self._on_upload_progress)
        self._upload_worker.finished_signal.connect(self._on_upload_finished)
        self._upload_worker.error_signal.connect(self._on_upload_error)
        self._upload_worker.start()

    def _resolve_duplicate_uploads(self, paths: List[Path], folder_name: str) -> List[Path]:
        if not paths:
            return []

        repo_path = self._current_repo_paths[0]
        folder_path = repo_path / folder_name
        existing = set()
        if folder_path.exists():
            for file_path in folder_path.iterdir():
                if file_path.is_file():
                    existing.add(file_path.name.lower())

        resolved: List[Path] = []
        temp_dir: Optional[Path] = None

        for src in paths:
            name_lc = src.name.lower()
            if name_lc not in existing:
                resolved.append(src)
                existing.add(name_lc)
                continue

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Duplicate image detected")
            msg.setText(f"'{src.name}' already exists in '{folder_name}'.")
            skip_btn = msg.addButton("Skip", QMessageBox.ButtonRole.RejectRole)
            replace_btn = msg.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
            keep_btn = msg.addButton("Keep Both", QMessageBox.ButtonRole.ActionRole)
            msg.setDefaultButton(keep_btn)
            msg.exec()
            clicked = msg.clickedButton()

            if clicked == skip_btn:
                continue
            if clicked == replace_btn:
                resolved.append(src)
                continue

            if temp_dir is None:
                temp_dir = Path(tempfile.mkdtemp(prefix="gitgallery_upload_"))
                self._temp_upload_dirs.append(temp_dir)

            unique_name = self._unique_filename(src.name, existing)
            existing.add(unique_name.lower())
            temp_copy = temp_dir / unique_name
            shutil.copy2(src, temp_copy)
            resolved.append(temp_copy)

        return resolved

    def _unique_filename(self, base_name: str, existing_lower: set[str]) -> str:
        path = Path(base_name)
        stem = path.stem
        suffix = path.suffix
        candidate = base_name
        index = 1
        while candidate.lower() in existing_lower:
            candidate = f"{stem} ({index}){suffix}"
            index += 1
        return candidate

    def _cleanup_temp_upload_dirs(self) -> None:
        for temp_dir in self._temp_upload_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_upload_dirs.clear()

    def ensure_github_and_repo(self) -> bool:
        """
        Ensure user is connected to GitHub and has selected a repo.
        Returns True if ready, False if user cancelled.
        """
        if not self._github.is_connected:
            dlg = ConnectGitHubDialog(self._github, self)
            if dlg.exec() != ConnectGitHubDialog.DialogCode.Accepted:
                return False
        if not self._current_repo_paths:
            dlg = RepoSelectorDialog(self._github, self)
            if dlg.exec() != RepoSelectorDialog.DialogCode.Accepted:
                return False
            owner, name, local_path, is_new = dlg.result()
            if local_path:
                self._current_repo_paths = get_physical_repos_for_folder(name or "")
                if not self._current_repo_paths:
                    self._current_repo_paths = [local_path]
                self._current_logical_folders = [name] if name else []
                self._show_gallery()
        return True
