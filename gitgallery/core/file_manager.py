"""
File and folder operations inside repository directories.

Handles listing folders/photos, copying uploads, and deleting files.
All paths are validated to prevent path traversal.
"""

import shutil
from pathlib import Path
from typing import List

from gitgallery.app.config import REPOS_DIR
from gitgallery.models.folder import Folder
from gitgallery.models.photo import Photo
from gitgallery.utils.helpers import (
    is_allowed_image_path,
    resolve_and_validate_inside_base,
    is_safe_folder_name,
    sanitize_folder_name,
)
from gitgallery.utils.logger import get_logger
from gitgallery.core.thumbnail_manager import get_thumbnail_path

logger = get_logger()


def list_folders(repo_path: Path) -> List[Folder]:
    """
    List all top-level directories in the repo as Folders.
    Only includes directories; each may contain images.
    """
    if not repo_path.is_dir():
        return []
    folders: List[Folder] = []
    for entry in repo_path.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            # Skip .git
            if entry.name == ".git":
                continue
            folders.append(
                Folder(
                    name=entry.name,
                    repo_path=repo_path,
                    relative_path=entry.name,
                )
            )
    return folders


def list_folders_across_repos(repo_paths: List[Path]) -> List[Folder]:
    """
    List unique folder names across multiple repo paths (for split repos).
    Aggregates by folder name; each Folder has the first repo_path that contains it.
    """
    seen: set[str] = set()
    result: List[Folder] = []
    for repo_path in repo_paths:
        for folder in list_folders(repo_path):
            if folder.name not in seen:
                seen.add(folder.name)
                result.append(folder)
    return result


def list_photos_in_folder(folder: Folder) -> List[Photo]:
    """List all image files in a folder. Sets thumbnail_path when possible."""
    photos: List[Photo] = []
    full = folder.full_path
    if not full.is_dir():
        return photos
    repo_name = folder.repo_path.name
    for f in full.iterdir():
        if f.is_file() and is_allowed_image_path(f):
            try:
                rel = f.relative_to(folder.repo_path)
                rel_str = str(rel)
                thumb = get_thumbnail_path(repo_name, rel_str)
                photos.append(
                    Photo(
                        file_path=f,
                        folder_relative_path=rel_str,
                        thumbnail_path=thumb if thumb.exists() else None,
                    )
                )
            except ValueError:
                continue
    return photos


def list_photos_in_folders(folders: List[Folder]) -> List[Photo]:
    """List all photos in a list of folders (e.g. same logical folder across splits)."""
    photos: List[Photo] = []
    for folder in folders:
        photos.extend(list_photos_in_folder(folder))
    return photos


def create_folder_in_repo(repo_path: Path, folder_name: str) -> Path:
    """
    Create a folder inside the repo. Validates folder_name.
    Returns the path to the new folder.
    """
    if not is_safe_folder_name(folder_name):
        raise ValueError("Invalid folder name")
    safe = sanitize_folder_name(folder_name)
    folder_path = resolve_and_validate_inside_base(repo_path, safe)
    folder_path.mkdir(parents=True, exist_ok=True)
    logger.info("Created folder %s in %s", safe, repo_path)
    return folder_path


def copy_upload_to_folder(
    repo_path: Path,
    folder_relative: str,
    source_path: Path,
    dest_filename: str | None = None,
) -> Path:
    """
    Copy an image file into the repository folder. Validates path and extension.
    Returns the path of the copied file inside the repo.
    """
    if not is_allowed_image_path(source_path):
        raise ValueError("File type not allowed")
    name = dest_filename or source_path.name
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("Invalid filename")
    dest_path = resolve_and_validate_inside_base(repo_path, folder_relative, name)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    logger.info("Copied %s -> %s", source_path.name, dest_path)
    return dest_path


def delete_photo(photo: Photo) -> None:
    """Delete the photo file from disk. Caller must run git rm and commit."""
    if photo.file_path.exists():
        photo.file_path.unlink()
        logger.info("Deleted file %s", photo.file_path)


def delete_photos(photos: List[Photo]) -> None:
    """Delete multiple photo files. Caller must run git rm and commit."""
    for p in photos:
        delete_photo(p)


def get_repo_path_for_folder_name(
    logical_folder_name: str,
    create_if_missing: bool = False,
) -> Path | None:
    """Return the primary (first) repo path for a logical folder, or None."""
    from gitgallery.core.repo_manager import get_physical_repos_for_folder
    paths = get_physical_repos_for_folder(logical_folder_name)
    if not paths:
        return None
    return paths[0]


def list_photos_from_gallery_index(
    repo_path: Path,
    repo_name: str,
) -> List[Photo]:
    """
    Build list of Photo from gallery index (avoids filesystem scan).
    Each photo has file_path and thumbnail_path set.
    """
    from gitgallery.core.repo_manager import gallery_index_get_photos
    photos: List[Photo] = []
    for folder_name, filename in gallery_index_get_photos(repo_name, repo_path):
        file_path = repo_path / folder_name / filename
        rel = f"{folder_name}/{filename}"
        thumb_path = get_thumbnail_path(repo_name, rel)
        photos.append(
            Photo(
                file_path=file_path,
                folder_relative_path=rel,
                thumbnail_path=thumb_path if thumb_path.exists() else None,
            )
        )
    return photos
