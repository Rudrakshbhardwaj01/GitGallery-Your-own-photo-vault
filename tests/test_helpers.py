"""Tests for path and validation helpers."""

import pytest
from pathlib import Path

from gitgallery.utils.helpers import (
    is_safe_folder_name,
    is_allowed_image_path,
    resolve_and_validate_inside_base,
    sanitize_folder_name,
)


def test_is_safe_folder_name() -> None:
    assert is_safe_folder_name("vacation") is True
    assert is_safe_folder_name("my-photos") is True
    assert is_safe_folder_name("") is False
    assert is_safe_folder_name("  ") is False
    assert is_safe_folder_name("a/ b") is False
    assert is_safe_folder_name("..") is False
    assert is_safe_folder_name("a\\b") is False


def test_is_allowed_image_path() -> None:
    assert is_allowed_image_path(Path("x.jpg")) is True
    assert is_allowed_image_path(Path("x.JPEG")) is True
    assert is_allowed_image_path(Path("x.png")) is True
    assert is_allowed_image_path(Path("x.gif")) is True
    assert is_allowed_image_path(Path("x.txt")) is False


def test_resolve_and_validate_inside_base(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    base.mkdir()
    p = resolve_and_validate_inside_base(base, "folder", "img.jpg")
    assert p == base / "folder" / "img.jpg"
    with pytest.raises(ValueError):
        resolve_and_validate_inside_base(base, "..", "etc")
    with pytest.raises(ValueError):
        resolve_and_validate_inside_base(base, "folder/../other")
