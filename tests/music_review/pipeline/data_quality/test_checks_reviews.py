"""Tests for reviews JSONL data-quality rules."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.data_quality.checks_reviews import scan_reviews_jsonl


def _review(rid: int, **kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": rid,
        "url": f"https://example.com/{rid}",
        "artist": "A",
        "album": "B",
        "text": "Some review body text that is long enough.",
    }
    base.update(kwargs)
    return base


def test_duplicate_review_id_is_error(tmp_path: Path) -> None:
    path = tmp_path / "reviews.jsonl"
    lines = [
        json.dumps(_review(1)),
        json.dumps(_review(1, text="other")),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    findings, stats = scan_reviews_jsonl(
        path,
        short_text_chars=50,
        year_min=1900,
        rating_min=0.0,
        rating_max=15.0,
        empty_text_warn_rate=0.01,
    )
    codes = {f.code for f in findings}
    assert "REVIEWS_DUPLICATE_ID" in codes
    assert any(f.severity == "error" for f in findings)
    assert 1 in stats.duplicate_ids


def test_non_empty_file_zero_valid_ids_is_error(tmp_path: Path) -> None:
    path = tmp_path / "reviews.jsonl"
    bad = {"id": "not-int", "url": "u", "artist": "a", "album": "b", "text": "t"}
    path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    findings, stats = scan_reviews_jsonl(
        path,
        short_text_chars=50,
        year_min=1900,
        rating_min=0.0,
        rating_max=15.0,
        empty_text_warn_rate=0.01,
    )
    assert stats.valid_review_count == 0
    assert any(f.code == "REVIEWS_ZERO_VALID" for f in findings)


def test_missing_reviews_file_warns(tmp_path: Path) -> None:
    path = tmp_path / "nope.jsonl"
    findings, _stats = scan_reviews_jsonl(
        path,
        short_text_chars=50,
        year_min=1900,
        rating_min=0.0,
        rating_max=15.0,
        empty_text_warn_rate=0.01,
    )
    assert any(f.code == "REVIEWS_FILE_MISSING" for f in findings)


def test_empty_text_rate_warn_above_threshold(tmp_path: Path) -> None:
    path = tmp_path / "reviews.jsonl"
    rows = [_review(i) for i in range(10)]
    rows[0] = _review(0, text="   ")
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    findings, _stats = scan_reviews_jsonl(
        path,
        short_text_chars=50,
        year_min=1900,
        rating_min=0.0,
        rating_max=15.0,
        empty_text_warn_rate=0.05,
    )
    assert any(f.code == "REVIEWS_EMPTY_TEXT_RATE" for f in findings)
