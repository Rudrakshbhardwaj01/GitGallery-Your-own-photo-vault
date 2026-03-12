"""
Repository and folder-index management.

Maintains repo_index.json: maps logical folder names to physical repo paths.
Handles automatic repository splitting when size or image count limits are exceeded.
"""

import json
from pathlib import Path
from typing import Dict, List

from gitgallery.app.config import (
    DATA_DIR,
    GALLERY_INDEX_FILENAME,
    MAX_IMAGES_PER_REPO,
    MAX_REPO_SIZE_BYTES,
    REPO_INDEX_FILENAME,
    REPOS_DIR,
)
from gitgallery.core import git_manager
from gitgallery.models.repository import Repository
from gitgallery.utils.logger import get_logger

logger = get_logger()


def _index_path() -> Path:
    """Path to repo_index.json in user data dir."""
    return DATA_DIR / REPO_INDEX_FILENAME


def load_repo_index() -> Dict[str, List[str]]:
    """
    Load repo_index.json. Keys are logical folder names; values are lists
    of physical repo directory names (under REPOS_DIR).
    """
    path = _index_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: list(v) if isinstance(v, list) else [v] for k, v in data.items()}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load repo index: %s", e)
        return {}


def save_repo_index(index: Dict[str, List[str]]) -> None:
    """Save repo_index.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _index_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    logger.debug("Saved repo index to %s", path)


def get_physical_repos_for_folder(logical_name: str) -> List[Path]:
    """Return list of repo paths (under REPOS_DIR) for a logical folder."""
    index = load_repo_index()
    names = index.get(logical_name, [])
    return [REPOS_DIR / n for n in names]


def register_repo(logical_folder_name: str, physical_repo_dir_name: str) -> None:
    """Register a single repo as the only physical repo for a logical folder."""
    index = load_repo_index()
    index[logical_folder_name] = [physical_repo_dir_name]
    save_repo_index(index)
    logger.info("Registered repo %s for folder %s", physical_repo_dir_name, logical_folder_name)


def append_split_repo(logical_folder_name: str, physical_repo_dir_name: str) -> None:
    """Add another physical repo to a logical folder (for splitting)."""
    index = load_repo_index()
    current = index.get(logical_folder_name, [])
    if physical_repo_dir_name not in current:
        current.append(physical_repo_dir_name)
        index[logical_folder_name] = current
        save_repo_index(index)
        logger.info("Appended split repo %s for folder %s", physical_repo_dir_name, logical_folder_name)


def list_logical_folders() -> List[str]:
    """Return all logical folder names from the index."""
    return list(load_repo_index().keys())


def get_repo_for_new_uploads(
    logical_folder_name: str,
    repo_paths: List[Path],
) -> Path:
    """
    Return the repo path that should receive new uploads (last one in split, or only one).
    Caller can then check size/count and create a new split if needed.
    """
    if not repo_paths:
        raise ValueError(f"No repos for folder {logical_folder_name}")
    return repo_paths[-1]


def folder_repo_size_and_count(repo_path: Path, folder_relative: str) -> tuple[int, int]:
    """Return (total_bytes, image_count) for the folder inside the repo."""
    folder_path = repo_path / folder_relative
    if not folder_path.is_dir():
        return 0, 0
    total = 0
    count = 0
    for f in folder_path.iterdir():
        if f.is_file():
            total += f.stat().st_size
            count += 1
    return total, count


def needs_new_split(repo_path: Path, folder_relative: str) -> bool:
    """True if the folder in this repo exceeds size or count limits."""
    size, count = folder_repo_size_and_count(repo_path, folder_relative)
    return size >= MAX_REPO_SIZE_BYTES or count >= MAX_IMAGES_PER_REPO


def create_and_register_split(
    logical_folder_name: str,
    remote_url: str,
    clone_dir_name: str,
) -> Path:
    """
    Clone a new repo (e.g. vacation2), add it to the index for the logical folder,
    and return its path. Caller must ensure the repo exists on GitHub first.
    """
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    local_path = REPOS_DIR / clone_dir_name
    git_manager.clone(remote_url, local_path)
    append_split_repo(logical_folder_name, clone_dir_name)
    return local_path


# ---------------------------------------------------------------------------
# Gallery index (avoids expensive filesystem scanning)
# Format: {"repo_name": {"folder_name": ["photo1.jpg", "photo2.jpg"]}}
# ---------------------------------------------------------------------------

def _gallery_index_path() -> Path:
    return DATA_DIR / GALLERY_INDEX_FILENAME


def load_gallery_index() -> Dict[str, Dict[str, List[str]]]:
    """Load gallery_index.json. Keys: repo_name -> folder_name -> list of filenames."""
    path = _gallery_index_path()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        out: Dict[str, Dict[str, List[str]]] = {}
        for repo, folders in data.items():
            if isinstance(folders, dict):
                out[repo] = {k: list(v) if isinstance(v, list) else [] for k, v in folders.items()}
        return out
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not load gallery index: %s", e)
        return {}


def save_gallery_index(index: Dict[str, Dict[str, List[str]]]) -> None:
    """Save gallery_index.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_gallery_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    logger.debug("Saved gallery index")


def gallery_index_add(repo_name: str, folder_name: str, filenames: List[str]) -> None:
    """Add filenames to gallery index for repo/folder."""
    index = load_gallery_index()
    if repo_name not in index:
        index[repo_name] = {}
    if folder_name not in index[repo_name]:
        index[repo_name][folder_name] = []
    for f in filenames:
        if f not in index[repo_name][folder_name]:
            index[repo_name][folder_name].append(f)
    save_gallery_index(index)


def gallery_index_remove(repo_name: str, folder_name: str, filenames: List[str]) -> None:
    """Remove filenames from gallery index."""
    index = load_gallery_index()
    if repo_name not in index or folder_name not in index[repo_name]:
        return
    for f in filenames:
        if f in index[repo_name][folder_name]:
            index[repo_name][folder_name].remove(f)
    if not index[repo_name][folder_name]:
        del index[repo_name][folder_name]
    if not index[repo_name]:
        del index[repo_name]
    save_gallery_index(index)


def gallery_index_get_photos(repo_name: str, repo_path: Path) -> List[tuple[str, str]]:
    """
    Return list of (folder_name, filename) from gallery index for repo.
    If index is empty for this repo, build from filesystem and save.
    """
    index = load_gallery_index()
    if repo_name in index and index[repo_name]:
        result: List[tuple[str, str]] = []
        for folder_name, filenames in index[repo_name].items():
            for fn in filenames:
                result.append((folder_name, fn))
        return result
    # Empty: build from filesystem once (avoid importing file_manager - circular)
    from gitgallery.app.config import ALLOWED_IMAGE_EXTENSIONS
    if not repo_path.is_dir():
        return []
    built: Dict[str, List[str]] = {}
    for entry in repo_path.iterdir():
        if entry.is_dir() and entry.name != ".git" and not entry.name.startswith("."):
            for f in entry.iterdir():
                if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                    if entry.name not in built:
                        built[entry.name] = []
                    built[entry.name].append(f.name)
    if built:
        index = load_gallery_index()
        index[repo_name] = built
        save_gallery_index(index)
    result = []
    for folder_name, filenames in built.items():
        for fn in filenames:
            result.append((folder_name, fn))
    return result
