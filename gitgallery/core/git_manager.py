"""
Git operations via CLI (subprocess).

Handles clone, add, commit, push, pull, rm. All Git operations for GitGallery
go through this module. Designed so encryption can be layered later.
"""

import subprocess
from pathlib import Path
from typing import List, Optional

from gitgallery.utils.logger import get_logger

logger = get_logger()


class GitError(Exception):
    """Raised when a Git command fails."""

    def __init__(self, message: str, stderr: Optional[str] = None) -> None:
        self.stderr = stderr
        super().__init__(message)


def _run_git(
    repo_path: Path,
    args: List[str],
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a Git command in the given repository directory.

    Args:
        repo_path: Path to the repository root.
        args: Git arguments (e.g. ['add', 'file.jpg']).
        check: If True, raise GitError on non-zero exit.
        capture: If True, capture stdout/stderr.

    Returns:
        CompletedProcess instance.

    Raises:
        GitError: If check=True and command fails.
        FileNotFoundError: If git executable is not found.
    """
    cmd = ["git"]
    cmd.extend(args)
    logger.debug("Running git in %s: %s", repo_path, " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            cwd=str(repo_path),
            capture_output=capture,
            text=True,
            timeout=300,
        )
    except FileNotFoundError as e:
        logger.error("Git not found: %s", e)
        raise
    except subprocess.TimeoutExpired as e:
        logger.error("Git command timed out: %s", e)
        raise GitError("Git command timed out") from e

    if check and result.returncode != 0:
        err = result.stderr.strip() if result.stderr else ""
        msg = f"Git failed (exit {result.returncode}): {' '.join(args)}"
        if err:
            msg += f" — {err}"
        logger.error("%s", msg)
        raise GitError(msg, stderr=err)

    return result


def is_git_installed() -> bool:
    """Return True if Git is available on the system."""
    try:
        _run_git(Path("."), ["--version"], check=True)
        return True
    except (FileNotFoundError, GitError):
        return False


def clone(remote_url: str, local_path: Path) -> None:
    """
    Clone a repository into local_path.

    Args:
        remote_url: Git URL (e.g. git@github.com:user/repo.git).
        local_path: Directory to clone into (must not exist or be empty).

    Raises:
        GitError: On clone failure (e.g. SSH auth, repo not found).
    """
    local_path = local_path.resolve()
    if local_path.exists() and any(local_path.iterdir()):
        raise GitError(f"Directory not empty: {local_path}")
    local_path.mkdir(parents=True, exist_ok=True)
    _run_git(local_path.parent, ["clone", "--depth", "1", remote_url, local_path.name])
    logger.info("Cloned %s into %s", remote_url, local_path)


def add(repo_path: Path, paths: List[Path]) -> None:
    """
    Stage files in the repository.

    Args:
        repo_path: Repository root.
        paths: Paths relative to repo_path or absolute (will be made relative).
    """
    rel_paths: List[str] = []
    for p in paths:
        p = Path(p)
        if p.is_absolute():
            try:
                rel = p.relative_to(repo_path.resolve())
            except ValueError:
                continue
        else:
            rel = p
        rel_paths.append(str(rel))
    if not rel_paths:
        return
    _run_git(repo_path, ["add", "--"] + rel_paths)
    logger.debug("Git add: %s", rel_paths)


def commit(repo_path: Path, message: str) -> None:
    """Create a commit with the given message."""
    _run_git(repo_path, ["commit", "-m", message])
    logger.info("Committed in %s: %s", repo_path, message[:50])


def push(repo_path: Path, remote: str = "origin", branch: str = "HEAD") -> None:
    """Push to remote. branch can be 'HEAD' or branch name."""
    _run_git(repo_path, ["push", remote, branch])
    logger.info("Pushed %s %s", remote, branch)


def pull(repo_path: Path, remote: str = "origin", branch: Optional[str] = None) -> None:
    """Pull from remote. If branch is None, uses current branch."""
    args = ["pull", remote]
    if branch:
        args.append(branch)
    _run_git(repo_path, args)
    logger.info("Pulled in %s", repo_path)


def rm(repo_path: Path, paths: List[Path], cached: bool = False) -> None:
    """
    Remove files from Git index (and optionally working tree).

    Args:
        repo_path: Repository root.
        paths: Paths relative to repo_path.
        cached: If True, only unstage (keep file on disk).
    """
    rel: List[str] = []
    for p in paths:
        r = Path(p)
        if r.is_absolute():
            try:
                r = r.relative_to(repo_path.resolve())
            except ValueError:
                continue
        rel.append(str(r))
    if not rel:
        return
    args = ["rm", "--cached"] if cached else ["rm", "-f"]
    _run_git(repo_path, args + ["--"] + rel)
    logger.debug("Git rm: %s", rel)


def has_uncommitted_changes(repo_path: Path) -> bool:
    """Return True if there are staged or unstaged changes."""
    try:
        r = _run_git(repo_path, ["status", "--porcelain"], check=True)
        return bool(r.stdout.strip())
    except GitError:
        return False


def has_commits(repo_path: Path) -> bool:
    """Return True if the repo has at least one commit."""
    try:
        _run_git(repo_path, ["rev-parse", "HEAD"], check=True)
        return True
    except GitError:
        return False


def get_current_branch(repo_path: Path) -> Optional[str]:
    """Return current branch name or None if detached."""
    try:
        r = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"], check=True)
        name = (r.stdout or "").strip()
        return name if name and name != "HEAD" else None
    except GitError:
        return None
