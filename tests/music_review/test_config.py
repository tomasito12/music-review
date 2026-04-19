"""Tests for shared configuration and path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.config import (
    DASHBOARD_SEMANTIC_SEARCH_ENABLED,
    get_project_root,
    get_recommendation_overall_weights,
    normalize_overall_weights,
    resolve_data_path,
)


def test_resolve_data_path_absolute_returns_unchanged() -> None:
    """An absolute path is returned as-is."""
    absolute = Path("/some/absolute/data/reviews.jsonl")
    assert resolve_data_path(absolute) == absolute
    assert resolve_data_path(str(absolute)) == absolute


def test_resolve_data_path_relative_joins_project_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A relative path is resolved against the project root."""
    fake_root = Path("/fake/project/root")
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(fake_root))
    # Clear any cached cwd-based result by re-importing or testing that env is used
    root = get_project_root()
    assert root == fake_root
    assert (
        resolve_data_path("data/reviews.jsonl") == fake_root / "data" / "reviews.jsonl"
    )
    assert resolve_data_path(Path("metadata.jsonl")) == fake_root / "metadata.jsonl"


def test_dashboard_semantic_search_disabled_by_default() -> None:
    """Product default: Filter-Flow Chroma chat expander stays off."""
    assert DASHBOARD_SEMANTIC_SEARCH_ENABLED is False


def test_get_recommendation_overall_weights_sum_to_one() -> None:
    a, b, c = get_recommendation_overall_weights()
    assert abs(a + b + c - 1.0) < 1e-9
    assert a > 0 and b > 0 and c > 0


def test_normalize_overall_weights_sum_to_one() -> None:
    a, b, c = normalize_overall_weights(2.0, 2.0, 4.0)
    assert abs(a + b + c - 1.0) < 1e-9
    assert abs(a - 0.25) < 1e-9 and abs(c - 0.5) < 1e-9


def test_normalize_overall_weights_all_zero_falls_back() -> None:
    a, b, c = normalize_overall_weights(0.0, 0.0, 0.0)
    assert abs(a + b + c - 1.0) < 1e-9
    assert abs(a - b) < 1e-9 and abs(b - c) < 1e-9


def test_get_project_root_returns_cwd_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When env var is unset, cwd is used as project root."""
    monkeypatch.delenv("MUSIC_REVIEW_PROJECT_ROOT", raising=False)
    root = get_project_root()
    assert root == Path.cwd()
