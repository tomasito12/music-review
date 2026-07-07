"""Tests for update batch JSONL persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from music_review.io.update_batches import (
    UpdateBatch,
    append_update_batch,
    ensure_scrape_batch_recorded,
    load_update_batches,
    review_ids_for_last_n_batches,
    update_batch_from_raw,
)


def test_update_batch_from_raw_parses_iso_timestamps() -> None:
    """Batch JSON rows become typed UpdateBatch objects."""
    batch = update_batch_from_raw(
        {
            "run_at": "2026-06-28T10:15:00Z",
            "review_ids": [101, 102],
            "count": 2,
        },
    )

    assert batch is not None
    assert batch.count == 2
    assert batch.review_ids == (101, 102)


def test_append_and_load_update_batches_round_trip(tmp_path: Path) -> None:
    """Append writes one JSONL row per scrape batch."""
    path = tmp_path / "update_batches.jsonl"
    run_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    append_update_batch([5, 6, 5], path=path, run_at=run_at)
    append_update_batch([7], path=path, run_at=run_at.replace(hour=13))

    batches = load_update_batches(path)
    assert len(batches) == 2
    assert batches[0].review_ids == (5, 6)
    assert batches[1].review_ids == (7,)


def test_review_ids_for_last_n_batches_uses_most_recent_runs() -> None:
    """Last-N selection unions ids from the newest batches only."""
    history = (
        UpdateBatch(datetime(2026, 6, 1, tzinfo=UTC), (1, 2)),
        UpdateBatch(datetime(2026, 6, 2, tzinfo=UTC), (3, 4)),
        UpdateBatch(datetime(2026, 6, 3, tzinfo=UTC), (5,)),
    )

    assert review_ids_for_last_n_batches(history, 1) == frozenset({5})
    assert review_ids_for_last_n_batches(history, 2) == frozenset({3, 4, 5})


def test_ensure_scrape_batch_recorded_skips_duplicate_latest_batch(
    tmp_path: Path,
) -> None:
    """Repeated scrape finalization does not append the same ids twice."""
    path = tmp_path / "update_batches.jsonl"

    first = ensure_scrape_batch_recorded([11, 12], path=path)
    second = ensure_scrape_batch_recorded([12, 11], path=path)

    assert first is not None
    assert second is not None
    assert first.review_ids == (11, 12)
    assert second.review_ids == (11, 12)
    assert len(load_update_batches(path)) == 1


def test_ensure_scrape_batch_recorded_appends_new_scrape_run(tmp_path: Path) -> None:
    """A new scrape run with different ids appends another batch row."""
    path = tmp_path / "update_batches.jsonl"

    ensure_scrape_batch_recorded([11, 12], path=path)
    ensure_scrape_batch_recorded([13], path=path)

    batches = load_update_batches(path)
    assert [batch.review_ids for batch in batches] == [(11, 12), (13,)]
