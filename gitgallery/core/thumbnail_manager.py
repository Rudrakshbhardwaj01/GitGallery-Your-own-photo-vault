"""
Thumbnail generation and lookup using Pillow.

Thumbnails are 300px width, stored in ~/GitGallery/thumbnails/.
Gallery loads only thumbnails; full images load only when previewing.
"""

import hashlib
from pathlib import Path
from typing import Optional

from PIL import Image

from gitgallery.app.config import THUMBNAILS_DIR, THUMBNAIL_WIDTH_PX
from gitgallery.utils.logger import get_logger

logger = get_logger()


def _thumbnail_key(repo_name: str, relative_path: str) -> str:
    """Stable key for thumbnail filename (avoids collisions across repos/folders)."""
    content = f"{repo_name}:{relative_path}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def get_thumbnail_path(repo_name: str, relative_path: str) -> Path:
    """Return path where thumbnail is or would be stored. Does not create it."""
    key = _thumbnail_key(repo_name, relative_path)
    ext = Path(relative_path).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    return THUMBNAILS_DIR / f"{key}{ext}"


def generate_thumbnail(
    source_path: Path,
    repo_name: str,
    relative_path: str,
) -> Path:
    """
    Generate thumbnail (300px width) and save to ~/GitGallery/thumbnails/.
    Returns path to the saved thumbnail file.
    """
    dest = get_thumbnail_path(repo_name, relative_path)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as img:
            img.load()
            ratio = THUMBNAIL_WIDTH_PX / img.width
            new_h = int(img.height * ratio)
            thumb = img.resize((THUMBNAIL_WIDTH_PX, new_h), Image.Resampling.LANCZOS)
            thumb.save(dest, quality=85, optimize=True)
        logger.debug("Generated thumbnail %s", dest.name)
        return dest
    except Exception as e:
        logger.warning("Thumbnail generation failed for %s: %s", source_path, e)
        raise
