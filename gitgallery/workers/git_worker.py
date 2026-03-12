"""
Background Git operations via QThread.

Prevents UI freezing during clone, add, commit, push, pull, rm.
"""

from pathlib import Path
from typing import Any, Callable, List, Optional

from PySide6.QtCore import QThread, Signal

from gitgallery.core import git_manager
from gitgallery.core.sync_manager import sync_all, SyncError
from gitgallery.utils.logger import get_logger

logger = get_logger()


class GitWorker(QThread):
    """
    Runs a single Git operation in a background thread.
    Signals: started, finished, error(str).
    """

    started_signal = Signal()
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(
        self,
        operation: str,
        repo_path: Optional[Path] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._op = operation
        self._repo_path = repo_path
        self._kwargs = kwargs
        self._result: Any = None

    def run(self) -> None:
        self.started_signal.emit()
        try:
            if self._op == "clone":
                git_manager.clone(
                    self._kwargs["remote_url"],
                    self._kwargs["local_path"],
                )
            elif self._op == "add":
                git_manager.add(self._repo_path, self._kwargs["paths"])
            elif self._op == "commit":
                git_manager.commit(self._repo_path, self._kwargs["message"])
            elif self._op == "push":
                git_manager.push(self._repo_path)
            elif self._op == "pull":
                git_manager.pull(self._repo_path)
            elif self._op == "rm":
                git_manager.rm(
                    self._repo_path,
                    self._kwargs["paths"],
                    cached=self._kwargs.get("cached", False),
                )
            elif self._op == "sync_all":
                sync_all()
            else:
                self.error_signal.emit(f"Unknown operation: {self._op}")
                return
            self.finished_signal.emit()
        except SyncError as e:
            logger.exception("Sync failed: %s", e)
            self.error_signal.emit(str(e))
        except git_manager.GitError as e:
            logger.exception("Git worker failed: %s", e)
            self.error_signal.emit(str(e))
        except Exception as e:
            logger.exception("Git worker error: %s", e)
            self.error_signal.emit(str(e))
