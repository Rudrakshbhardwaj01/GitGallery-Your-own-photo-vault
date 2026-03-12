"""
Helper utilities for path validation and safe file operations.

Prevents path traversal and validates folder names and image types.
"""

from pathlib import Path
from typing import List

from gitgallery.app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_FOLDER_NAME_LENGTH,
    MAX_PATH_COMPONENTS,
)


def is_safe_folder_name(name: str) -> bool:
    """
    Check that a folder name is safe (no path traversal, reasonable length).

    Args:
        name: Candidate folder name.

    Returns:
        True if the name is safe to use.
    """
    if not name or not name.strip():
        return False
    clean = name.strip()
    if len(clean) > MAX_FOLDER_NAME_LENGTH:
        return False
    if ".." in clean or "/" in clean or "\\" in clean:
        return False
    if any(c in clean for c in '\0\r\n\t'):
        return False
    return True


def is_allowed_image_path(path: Path) -> bool:
    """
    Check if a file path has an allowed image extension.

    Args:
        path: File path (file or Path object).

    Returns:
        True if the extension is in ALLOWED_IMAGE_EXTENSIONS (case-insensitive).
    """
    suffix = path.suffix.lower()
    return suffix in ALLOWED_IMAGE_EXTENSIONS


def resolve_and_validate_inside_base(
    base: Path,
    *parts: str,
) -> Path:
    """
    Resolve a path from base and ensure it stays inside base (no path traversal).

    Args:
        base: Base directory (e.g. repo root).
        *parts: Path components (folder names, file names).

    Returns:
        Resolved path normalized and checked to be under base.

    Raises:
        ValueError: If the resolved path is outside base or too deep.
    """
    if len(parts) > MAX_PATH_COMPONENTS:
        raise ValueError("Path has too many components")
    for p in parts:
        if ".." in p or "/" in p or "\\" in p:
            raise ValueError("Invalid path component")
    resolved = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError("Path would escape base directory") from None
    return resolved


def sanitize_folder_name(name: str) -> str:
    """
    Return a sanitized folder name safe for filesystem use.

    Strips whitespace and replaces characters that are problematic in paths.
    """
    clean = name.strip()
    if not clean:
        return clean
    # Disallow path separators and control chars
    result: List[str] = []
    for c in clean:
        if c in "/\\\0\r\n\t" or ord(c) < 32:
            result.append("_")
        else:
            result.append(c)
    out = "".join(result)[:MAX_FOLDER_NAME_LENGTH]
    return out.rstrip(" .")
