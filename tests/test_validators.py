"""Tests for validators."""

import pytest
from pathlib import Path

from gitgallery.utils.validators import (
    ValidationError,
    validate_image_extension,
    validate_image_size,
    validate_image_file,
    validate_folder_name,
    validate_path_inside_base,
)


def test_validate_image_extension() -> None:
    validate_image_extension(Path("x.jpg"))
    validate_image_extension(Path("x.JPEG"))
    validate_image_extension(Path("x.png"))
    validate_image_extension(Path("x.webp"))
    with pytest.raises(ValidationError):
        validate_image_extension(Path("x.gif"))
    with pytest.raises(ValidationError):
        validate_image_extension(Path("x.txt"))


def test_validate_image_size(tmp_path: Path) -> None:
    small = tmp_path / "small.jpg"
    small.write_bytes(b"x")
    validate_image_size(small)
    large = tmp_path / "large.jpg"
    large.write_bytes(b"x" * (21 * 1024 * 1024))
    with pytest.raises(ValidationError):
        validate_image_size(large)


def test_validate_image_file(tmp_path: Path) -> None:
    ok = tmp_path / "ok.png"
    ok.write_bytes(b"png content")
    validate_image_file(ok)
    with pytest.raises(ValidationError):
        validate_image_file(Path("bad.gif"))
    too_big = tmp_path / "big.jpg"
    too_big.write_bytes(b"x" * (21 * 1024 * 1024))
    with pytest.raises(ValidationError):
        validate_image_file(too_big)


def test_validate_folder_name() -> None:
    validate_folder_name("vacation")
    validate_folder_name("my-photos")
    with pytest.raises(ValidationError):
        validate_folder_name("")
    with pytest.raises(ValidationError):
        validate_folder_name("a/b")
    with pytest.raises(ValidationError):
        validate_folder_name("..")


def test_validate_path_inside_base(tmp_path: Path) -> None:
    base = tmp_path / "repo"
    base.mkdir()
    p = validate_path_inside_base(base, "folder", "img.jpg")
    assert p == base / "folder" / "img.jpg"
    with pytest.raises(ValidationError):
        validate_path_inside_base(base, "..", "etc")
    with pytest.raises(ValidationError):
        validate_path_inside_base(base, "folder/../other")
