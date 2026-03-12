"""
Repository model for GitGallery.

Represents a logical folder that may map to one or more Git repositories
when automatic splitting is used.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Repository:
    """
    A Git repository used for photo storage.

    For split repositories, the logical_folder_name is the user-facing name
    (e.g. 'vacation') and physical_repo_paths are the actual clone paths
    (e.g. vacation, vacation1, vacation2).
    """

    logical_folder_name: str
    """User-facing folder name (e.g. 'vacation')."""

    physical_repo_paths: List[Path] = field(default_factory=list)
    """Paths to local clones (e.g. [repos/vacation, repos/vacation1])."""

    remote_url: str = ""
    """Git remote URL (e.g. git@github.com:user/repo.git)."""

    def primary_path(self) -> Path:
        """Return the first (primary) repository path."""
        if not self.physical_repo_paths:
            return Path()
        return self.physical_repo_paths[0]

    def all_paths(self) -> List[Path]:
        """Return all physical repository paths."""
        return list(self.physical_repo_paths)
