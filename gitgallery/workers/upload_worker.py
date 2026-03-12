"""
Background upload workflow: copy files, generate thumbnails, update index.

Git add/commit/push are run separately (e.g. via GitWorker) after this finishes.
"""

from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from gitgallery.app.config import REPOS_DIR
from gitgallery.core.file_manager import copy_upload_to_folder, create_folder_in_repo
from gitgallery.core.thumbnail_manager import generate_thumbnail
from gitgallery.core.repo_manager import gallery_index_add
from gitgallery.utils.validators import validate_image_file, ValidationError
from gitgallery.utils.logger import get_logger

logger = get_logger()


class UploadWorker(QThread):
    """
    Copies images to repo folder, generates thumbnails, updates gallery index.
    Does NOT run git commands; caller runs GitWorker after this.
    Signals: started, progress(current, total), finished(added_paths), error(str).
    """

    started_signal = Signal()
    progress_signal = Signal(int, int)
    finished_signal = Signal(object)  # list of Path
    error_signal = Signal(str)

    def __init__(
        self,
        repo_path: Path,
        repo_name: str,
        folder_name: str,
        source_paths: List[Path],
    ) -> None:
        super().__init__()
        self._repo_path = repo_path
        self._repo_name = repo_name
        self._folder_name = folder_name
        self._source_paths = list(source_paths)

    def run(self) -> None:
        self.started_signal.emit()
        added: List[Path] = []
        total = len(self._source_paths)
        try:
            create_folder_in_repo(self._repo_path, self._folder_name)
        except Exception:
            pass  # may already exist
        for i, src in enumerate(self._source_paths):
            try:
                validate_image_file(src)
            except ValidationError as e:
                self.error_signal.emit(str(e))
                return
            try:
                dest = copy_upload_to_folder(
                    self._repo_path,
                    self._folder_name,
                    src,
                )
                added.append(dest)
                generate_thumbnail(dest, self._repo_name, f"{self._folder_name}/{dest.name}")
            except Exception as e:
                logger.exception("Upload failed for %s: %s", src, e)
                self.error_signal.emit(f"{src.name}: {e}")
                return
            self.progress_signal.emit(i + 1, total)
        if added:
            filenames = [p.name for p in added]
            gallery_index_add(self._repo_name, self._folder_name, filenames)
        self.finished_signal.emit(added)
