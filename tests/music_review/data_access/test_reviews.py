"""Tests for review corpus scans in data_access."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.data_access.reviews import (
    max_release_year_in_jsonl,
    min_release_year_in_jsonl,
    plattenlabel_album_count_buckets_from_reviews_jsonl,
    review_raw_release_year,
    unique_plattenlabels_from_reviews_jsonl,
)


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_review_raw_release_year_from_year_field() -> None:
    assert review_raw_release_year({"release_year": 1999}) == 1999


def test_review_raw_release_year_from_iso_date() -> None:
    assert review_raw_release_year({"release_date": "2001-05-12"}) == 2001


def test_max_and_min_release_year_in_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "reviews.jsonl"
    _write_rows(
        p,
        [
            {"id": 1, "release_year": 1988},
            {"id": 2, "release_date": "2024-01-01"},
        ],
    )
    assert min_release_year_in_jsonl(p) == 1988
    assert max_release_year_in_jsonl(p) == 2024


def test_max_release_year_missing_file(tmp_path: Path) -> None:
    assert max_release_year_in_jsonl(tmp_path / "missing.jsonl") is None


def test_unique_plattenlabels_from_reviews_jsonl(tmp_path: Path) -> None:
    p = tmp_path / "reviews.jsonl"
    _write_rows(
        p,
        [
            {"id": 1, "labels": ["B", "A"]},
            {"id": 2, "labels": ["A"]},
        ],
    )
    assert unique_plattenlabels_from_reviews_jsonl(p) == ["A", "B"]


def test_plattenlabel_buckets_split_frequent_and_rare(tmp_path: Path) -> None:
    p = tmp_path / "reviews.jsonl"
    rows = [{"id": i, "labels": ["Common"]} for i in range(1, 52)]
    rows.append({"id": 99, "labels": ["Rare"]})
    _write_rows(p, rows)
    frequent, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
        p,
        min_albums_exclusive=50,
    )
    assert n == 52
    assert frequent == ["Common"]
    assert rare == ["Rare"]
