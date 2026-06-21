"""Tests for dashboard cache keys tied to data files."""

from __future__ import annotations

from pathlib import Path

from music_review.dashboard.cache_keys import call_file_cached, file_cache_signature


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


def test_call_file_cached_passes_signature_to_loader(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    seen: list[tuple[bool, int, int]] = []

    def loader(sig: tuple[bool, int, int]) -> str:
        seen.append(sig)
        return "ok"

    assert call_file_cached(loader, path) == "ok"
    assert seen == [file_cache_signature(path)]
