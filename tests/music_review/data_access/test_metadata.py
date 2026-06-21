"""Tests for metadata loading with imputed preference."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.data_access.metadata import load_metadata_map, resolve_metadata_path


def test_resolve_metadata_path_prefers_imputed(tmp_path: Path) -> None:
    raw = tmp_path / "metadata.jsonl"
    imputed = tmp_path / "metadata_imputed.jsonl"
    raw.write_text(json.dumps({"review_id": 1}) + "\n", encoding="utf-8")
    imputed.write_text(json.dumps({"review_id": 2}) + "\n", encoding="utf-8")
    assert resolve_metadata_path(imputed=imputed, raw=raw) == imputed


def test_resolve_metadata_path_falls_back_to_raw(tmp_path: Path) -> None:
    raw = tmp_path / "metadata.jsonl"
    imputed = tmp_path / "metadata_imputed.jsonl"
    raw.write_text(json.dumps({"review_id": 1, "artist": "A"}) + "\n", encoding="utf-8")
    assert resolve_metadata_path(imputed=imputed, raw=raw) == raw


def test_load_metadata_map_returns_review_id_index(tmp_path: Path) -> None:
    path = tmp_path / "metadata_imputed.jsonl"
    path.write_text(
        json.dumps({"review_id": 7, "labels": ["X"]}) + "\n",
        encoding="utf-8",
    )
    loaded = load_metadata_map(imputed=path, raw=tmp_path / "missing.jsonl")
    assert loaded[7]["labels"] == ["X"]
