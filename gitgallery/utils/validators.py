"""
Validation for security and business rules.

Validates image types, file size (20MB max), folder names, and path traversal.
"""

from pathlib import Path
from typing import Optional

from gitgallery.app.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_FOLDER_NAME_LENGTH,
    MAX_PATH_COMPONENTS,
)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_image_extension(path: Path) -> None:
    """Raise ValidationError if file extension is not allowed (jpg, jpeg, png, webp)."""
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"File type not allowed: {suffix}. Allowed: jpg, jpeg, png, webp."
        )


def validate_image_size(path: Path) -> None:
    """Raise ValidationError if file size exceeds 20MB."""
    if not path.is_file():
        raise ValidationError("Path is not a file.")
    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File too large: {size / (1024*1024):.1f}MB. Maximum is 20MB."
        )


def validate_image_file(path: Path) -> None:
    """Validate that path is an allowed image type and within size limit. Raises ValidationError."""
    validate_image_extension(path)
    validate_image_size(path)


def validate_folder_name(name: str) -> None:
    """Raise ValidationError if folder name is invalid (path traversal, length, etc.)."""
    if not name or not name.strip():
        raise ValidationError("Folder name cannot be empty.")
    clean = name.strip()
    if len(clean) > MAX_FOLDER_NAME_LENGTH:
        raise ValidationError(f"Folder name too long (max {MAX_FOLDER_NAME_LENGTH}).")
    if ".." in clean or "/" in clean or "\\" in clean:
        raise ValidationError("Folder name cannot contain .. or path separators.")
    if any(c in clean for c in "\0\r\n\t"):
        raise ValidationError("Folder name contains invalid characters.")


def validate_path_inside_base(base: Path, *parts: str) -> Path:
    """
    Resolve path from base and parts; raise ValidationError if outside base (path traversal).
    """
    if len(parts) > MAX_PATH_COMPONENTS:
        raise ValidationError("Path has too many components.")
    for p in parts:
        if ".." in p or "/" in p or "\\" in p:
            raise ValidationError("Invalid path component.")
    resolved = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValidationError("Path would escape base directory.") from None
    return resolved
