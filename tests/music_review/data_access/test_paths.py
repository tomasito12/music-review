"""Tests for central data path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.data_access.paths import (
    DATA_REVIEWS,
    album_community_affinities_path,
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
