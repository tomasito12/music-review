"""Tests for album affinity loading and projections."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.data_access.affinities import (
    affinities_by_review_id,
    affinities_list,
    load_affinities_raw,
    top_communities_per_review,
)


def _write_affinities(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _sample_row(review_id: int = 1) -> dict[str, object]:
    return {
        "review_id": review_id,
        "communities": {
            "res_10": [
                {"id": "C001", "score": 0.2},
                {"id": "C002", "score": 0.8},
                {"id": "C003", "score": 0.5},
            ],
        },
    }


def test_load_affinities_raw_skips_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / "affinities.jsonl"
    _write_affinities(
        path,
        [
            _sample_row(1),
            {"review_id": 2},
            {"communities": {}},
        ],
    )
    rows = load_affinities_raw(path)
    assert len(rows) == 1
    assert rows[0]["review_id"] == 1


def test_affinities_by_review_id_maps_rows(tmp_path: Path) -> None:
    path = tmp_path / "affinities.jsonl"
    _write_affinities(path, [_sample_row(3), _sample_row(4)])
    by_id = affinities_by_review_id(path)
    assert set(by_id) == {3, 4}


def test_affinities_list_matches_raw_loader(tmp_path: Path) -> None:
    path = tmp_path / "affinities.jsonl"
    _write_affinities(path, [_sample_row(1), _sample_row(2)])
    assert affinities_list(path) == load_affinities_raw(path)


def test_top_communities_per_review_orders_and_limits(tmp_path: Path) -> None:
    path = tmp_path / "affinities.jsonl"
    _write_affinities(path, [_sample_row(9)])
    top = top_communities_per_review(path=path, top_k=2)
    assert top[9] == [("C002", 0.8), ("C003", 0.5)]


def test_top_communities_empty_when_file_missing(tmp_path: Path) -> None:
    assert top_communities_per_review(path=tmp_path / "missing.jsonl") == {}
