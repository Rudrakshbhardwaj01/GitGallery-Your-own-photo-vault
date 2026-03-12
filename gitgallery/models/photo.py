"""
Photo model for GitGallery.

Represents a single image file in a folder.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Photo:
    """
    A photo (image file) in a folder.

    file_path: Absolute path to the image file.
    folder_relative_path: Path of the file relative to repo root (e.g. folder/img.jpg).
    thumbnail_path: Optional path to cached thumbnail in ~/GitGallery/thumbnails/.
    """

    file_path: Path
    folder_relative_path: str
    thumbnail_path: Optional[Path] = None

    @property
    def name(self) -> str:
        """File name of the photo."""
        return self.file_path.name
