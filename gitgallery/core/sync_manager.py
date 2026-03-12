"""
Sync operations: git pull and push.

Orchestrates pull (to get remote changes) and push (when local commits exist).
"""

from pathlib import Path
from typing import List, Optional

from gitgallery.core import git_manager
from gitgallery.core.repo_manager import get_physical_repos_for_folder, load_repo_index
from gitgallery.app.config import REPOS_DIR
from gitgallery.utils.logger import get_logger

logger = get_logger()


class SyncError(Exception):
    """Raised when sync fails (e.g. merge conflict, push rejected)."""

    def __init__(self, message: str, repo_path: Optional[Path] = None) -> None:
        self.repo_path = repo_path
        super().__init__(message)


def sync_repo(repo_path: Path) -> None:
    """
    Pull then push for a single repo.
    On pull conflict, raises SyncError; on push failure, raises SyncError.
    """
    try:
        git_manager.pull(repo_path)
    except git_manager.GitError as e:
        if "merge" in (e.stderr or "").lower() or "conflict" in (e.stderr or "").lower():
            raise SyncError(f"Merge conflict in {repo_path.name}. Resolve manually.", repo_path=repo_path) from e
        raise SyncError(str(e), repo_path=repo_path) from e

    # If local commits exist, push them
    try:
        git_manager.push(repo_path)
    except git_manager.GitError as e:
        raise SyncError(str(e), repo_path=repo_path) from e


def sync_all() -> List[Path]:
    """
    Sync all repositories in the index (pull then push for each).
    Returns list of repo paths that were synced successfully.
    """
    index = load_repo_index()
    synced: List[Path] = []
    for logical_name, repo_names in index.items():
        for name in repo_names:
            repo_path = REPOS_DIR / name
            if not repo_path.is_dir():
                logger.warning("Repo path missing: %s", repo_path)
                continue
            try:
                sync_repo(repo_path)
                synced.append(repo_path)
            except SyncError as e:
                logger.error("Sync failed for %s: %s", repo_path, e)
                raise
    return synced
