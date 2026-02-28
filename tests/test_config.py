"""Tests for shared configuration and path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.config import get_project_root, resolve_data_path


def test_resolve_data_path_absolute_returns_unchanged() -> None:
    """An absolute path is returned as-is."""
    absolute = Path("/some/absolute/data/reviews.jsonl")
    assert resolve_data_path(absolute) == absolute
    assert resolve_data_path(str(absolute)) == absolute


def test_resolve_data_path_relative_joins_project_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """A relative path is resolved against the project root."""
    fake_root = Path("/fake/project/root")
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(fake_root))
    # Clear any cached cwd-based result by re-importing or testing that env is used
    root = get_project_root()
    assert root == fake_root
    assert resolve_data_path("data/reviews.jsonl") == fake_root / "data" / "reviews.jsonl"
    assert resolve_data_path(Path("metadata.jsonl")) == fake_root / "metadata.jsonl"


def test_get_project_root_returns_cwd_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """When MUSIC_REVIEW_PROJECT_ROOT is not set, get_project_root returns current working directory."""
    monkeypatch.delenv("MUSIC_REVIEW_PROJECT_ROOT", raising=False)
    root = get_project_root()
    assert root == Path.cwd()
