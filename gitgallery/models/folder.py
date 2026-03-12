"""
Folder model for GitGallery.

Represents a user-visible folder (photo collection) inside a repository.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from gitgallery.models.photo import Photo


@dataclass
class Folder:
    """
    A folder (collection) of photos inside a repository.

    name: User-visible folder name.
    repo_path: Path to the local repo root that contains this folder.
    relative_path: Path relative to repo root (e.g. 'vacation' or 'family').
    """

    name: str
    repo_path: Path
    relative_path: str
    photos: List[Photo] = field(default_factory=list)

    @property
    def full_path(self) -> Path:
        """Absolute path to the folder on disk."""
        return self.repo_path / self.relative_path
