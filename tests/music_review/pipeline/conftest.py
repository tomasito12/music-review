"""Shared fixtures for pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_pipeline_data_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Keep pipeline side effects out of the workspace data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(tmp_path))
    return data_dir
