"""Tests for newest review pool resolution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from music_review.application.newest_review_pool import newest_reviews_for_update_rounds
from music_review.domain.models import Review
from music_review.io.update_batches import append_update_batch


def test_newest_reviews_for_update_rounds_reads_batch_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """API pool resolution uses stored scrape batches when available."""
    batches_path = tmp_path / "update_batches.jsonl"
    append_update_batch([2], path=batches_path, run_at=datetime(2026, 6, 1, tzinfo=UTC))
    append_update_batch([3], path=batches_path, run_at=datetime(2026, 6, 2, tzinfo=UTC))

    monkeypatch.setattr(
        "music_review.application.newest_review_pool.update_batches_path",
        lambda: batches_path,
    )

    reviews = [
        Review(1, "https://example.com/1", "A1", "B1", "t"),
        Review(2, "https://example.com/2", "A2", "B2", "t"),
        Review(3, "https://example.com/3", "A3", "B3", "t"),
    ]

    selected = newest_reviews_for_update_rounds(reviews, 1)

    assert [review.id for review in selected] == [3]
