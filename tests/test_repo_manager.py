"""Tests for repo_manager."""

import pytest
from pathlib import Path

from gitgallery.core.repo_manager import (
    load_repo_index,
    save_repo_index,
    load_gallery_index,
    save_gallery_index,
    gallery_index_add,
    gallery_index_remove,
    get_physical_repos_for_folder,
    register_repo,
)


def test_repo_index_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("gitgallery.core.repo_manager.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "gitgallery.core.repo_manager._index_path",
        lambda: tmp_path / "repo_index.json",
    )
    save_repo_index({"vacation": ["vacation", "vacation1"], "family": ["family"]})
    loaded = load_repo_index()
    assert loaded["vacation"] == ["vacation", "vacation1"]
    assert loaded["family"] == ["family"]


def test_gallery_index_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("gitgallery.core.repo_manager.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "gitgallery.core.repo_manager._gallery_index_path",
        lambda: tmp_path / "gallery_index.json",
    )
    save_gallery_index({"repo1": {"folder1": ["a.jpg", "b.png"]}})
    loaded = load_gallery_index()
    assert loaded["repo1"]["folder1"] == ["a.jpg", "b.png"]


def test_gallery_index_add_remove(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("gitgallery.core.repo_manager.DATA_DIR", tmp_path)
    monkeypatch.setattr(
        "gitgallery.core.repo_manager._gallery_index_path",
        lambda: tmp_path / "gallery_index.json",
    )
    gallery_index_add("r1", "f1", ["a.jpg", "b.jpg"])
    assert load_gallery_index()["r1"]["f1"] == ["a.jpg", "b.jpg"]
    gallery_index_add("r1", "f1", ["c.jpg"])
    assert load_gallery_index()["r1"]["f1"] == ["a.jpg", "b.jpg", "c.jpg"]
    gallery_index_remove("r1", "f1", ["b.jpg"])
    assert load_gallery_index()["r1"]["f1"] == ["a.jpg", "c.jpg"]
    gallery_index_remove("r1", "f1", ["a.jpg", "c.jpg"])
    idx = load_gallery_index()
    assert "r1" not in idx or "f1" not in idx.get("r1", {})
