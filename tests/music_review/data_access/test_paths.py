"""Tests for central data path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.data_access.paths import (
    DATA_ARTIST_REFERENCE_GRAPH,
    DATA_COMMUNITY_RESOLUTION_SCAN,
    DATA_DIR,
    DATA_METADATA,
    DATA_REVIEWS,
    album_community_affinities_path,
    artist_reference_graph_path,
    community_resolution_scan_path,
    data_dir,
    metadata_path,
    reviews_path,
)


def test_reviews_path_uses_resolve_data_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(tmp_path))
    p = reviews_path()
    assert p == tmp_path / DATA_REVIEWS
    assert album_community_affinities_path().parent == tmp_path / "data"


def test_data_dir_and_graph_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(tmp_path))
    assert data_dir() == tmp_path / DATA_DIR
    assert artist_reference_graph_path() == tmp_path / DATA_ARTIST_REFERENCE_GRAPH
    assert community_resolution_scan_path() == tmp_path / DATA_COMMUNITY_RESOLUTION_SCAN
    assert metadata_path() == tmp_path / DATA_METADATA
