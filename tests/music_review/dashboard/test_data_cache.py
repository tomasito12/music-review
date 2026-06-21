"""Tests for Streamlit cache wrappers over data_access."""

from __future__ import annotations

import pytest

from music_review.dashboard import data_cache


def test_cached_loaders_delegate_to_data_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(data_cache, "load_communities_res_10", lambda: [{"id": "C001"}])
    assert data_cache._load_communities_res_10_cached((True, 1, 1)) == [{"id": "C001"}]
