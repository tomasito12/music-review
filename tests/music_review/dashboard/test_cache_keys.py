"""Tests for dashboard cache keys tied to data files."""

from __future__ import annotations

from pathlib import Path

from music_review.dashboard.cache_keys import file_cache_signature


def test_missing_file_has_stable_empty_signature(tmp_path: Path) -> None:
    path = tmp_path / "missing.jsonl"

    assert file_cache_signature(path) == (False, 0, 0)


def test_file_signature_changes_when_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "reviews.jsonl"
    path.write_text('{"id": 1}\n', encoding="utf-8")
    before = file_cache_signature(path)

    path.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
    after = file_cache_signature(path)

    assert before[0] is True
    assert after[0] is True
    assert after != before
