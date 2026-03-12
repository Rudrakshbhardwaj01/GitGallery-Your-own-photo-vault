"""
Repository selector UI.

Shows list of user's GitHub repositories and option to create a new one.
User selects one repo or creates a new repository (via API then clone).
"""

from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QInputDialog,
    QProgressBar,
    QGroupBox,
)
from PySide6.QtGui import QFont

from gitgallery.core.github_connector import GitHubConnector, GitHubAPIError
from gitgallery.core import git_manager
from gitgallery.app.config import REPOS_DIR
from gitgallery.core.repo_manager import register_repo
from gitgallery.utils.logger import get_logger
from gitgallery.ui.theme import apply_dark_theme

logger = get_logger()


class RepoSelectorDialog(QDialog):
    """
    After GitHub connection: list repos, select one or create new.
    On success, returns (repo_owner, repo_name, local_path, is_new).
    """

    def __init__(
        self,
        github: GitHubConnector,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._github = github
        self._repos: List[dict] = []
        self._selected_owner: Optional[str] = None
        self._selected_name: Optional[str] = None
        self._local_path: Optional[Path] = None
        self._is_new: bool = False
        self.setWindowTitle("Select Repository")
        self.setMinimumSize(560, 430)
        self._build_ui()
        self._load_repos()

    def _build_ui(self) -> None:
        apply_dark_theme(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Repositories")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Choose an existing GitHub repository or create a new private one.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setProperty("muted", True)
        layout.addWidget(subtitle)

        self._list = QListWidget()
        self._list.setMinimumHeight(220)
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)

        self._create_btn = QPushButton("Create New Repository")
        self._create_btn.setProperty("accent", True)
        self._create_btn.style().unpolish(self._create_btn)
        self._create_btn.style().polish(self._create_btn)
        self._create_btn.clicked.connect(self._create_new)
        layout.addWidget(self._create_btn)

        btn_layout = QHBoxLayout()
        self._select_btn = QPushButton("Use Selected")
        self._select_btn.setProperty("accent", True)
        self._select_btn.style().unpolish(self._select_btn)
        self._select_btn.style().polish(self._select_btn)
        self._select_btn.clicked.connect(self._on_select_clicked)
        btn_layout.addWidget(self._select_btn)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        layout.addLayout(btn_layout)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        layout.addWidget(self._progress)

    def _load_repos(self) -> None:
        try:
            self._repos = self._github.list_repositories()
        except GitHubAPIError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not load repositories: {e}",
            )
            return
        self._list.clear()
        for r in self._repos:
            name = r.get("full_name") or r.get("name") or "?"
            private = " (private)" if r.get("private") else ""
            item = QListWidgetItem(f"{name}{private}")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def _on_select_clicked(self) -> None:
        self._on_select(self._list.currentItem())

    def _on_select(self, item: Optional[QListWidgetItem]) -> None:
        if not item:
            QMessageBox.information(self, "Select", "Please select a repository.")
            return
        repo = item.data(Qt.ItemDataRole.UserRole)
        if not repo:
            return
        full_name = repo.get("full_name") or repo.get("name")
        if not full_name:
            return
        parts = full_name.split("/", 1)
        owner = parts[0]
        name = parts[1] if len(parts) > 1 else full_name
        clone_url = repo.get("ssh_url") or repo.get("clone_url")
        if not clone_url:
            QMessageBox.critical(self, "Error", "Repository has no clone URL.")
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()

        try:
            local_name = name
            local_path = REPOS_DIR / local_name
            if local_path.exists() and (local_path / ".git").exists():
                self._selected_owner = owner
                self._selected_name = name
                self._local_path = local_path
                self._is_new = False
                register_repo(name, local_name)
                self.accept()
                return
            REPOS_DIR.mkdir(parents=True, exist_ok=True)
            git_manager.clone(clone_url, local_path)
            register_repo(name, local_name)
            self._selected_owner = owner
            self._selected_name = name
            self._local_path = local_path
            self._is_new = False
            self.accept()
        except git_manager.GitError as e:
            QMessageBox.critical(
                self,
                "Clone Failed",
                f"Could not clone repository:\n{e}",
            )
        except Exception as e:
            logger.exception("Repo select error")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self._progress.setVisible(False)

    def _create_new(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            "New Repository",
            "Repository name:",
            text="gitgallery-storage",
        )
        if not ok or not name or not name.strip():
            return
        name = name.strip()
        if "/" in name or " " in name:
            QMessageBox.warning(self, "Invalid", "Repository name cannot contain / or spaces.")
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        QApplication.processEvents()

        try:
            repo = self._github.create_repository(name, private=True)
            clone_url = repo.get("ssh_url") or repo.get("clone_url")
            if not clone_url:
                raise GitHubAPIError("New repo has no clone URL")
            local_path = REPOS_DIR / name
            REPOS_DIR.mkdir(parents=True, exist_ok=True)
            git_manager.clone(clone_url, local_path)
            register_repo(name, name)
            self._selected_owner = repo.get("owner", {}).get("login", "")
            self._selected_name = name
            self._local_path = local_path
            self._is_new = True
            self.accept()
        except GitHubAPIError as e:
            QMessageBox.critical(self, "Create Failed", f"GitHub API: {e}")
        except git_manager.GitError as e:
            QMessageBox.critical(self, "Clone Failed", f"Could not clone: {e}")
        except Exception as e:
            logger.exception("Create repo error")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self._progress.setVisible(False)

    def result(self) -> tuple[Optional[str], Optional[str], Optional[Path], bool]:
        """Return (owner, repo_name, local_path, is_new) or (None, None, None, False)."""
        return (
            self._selected_owner,
            self._selected_name,
            self._local_path,
            self._is_new,
        )
