"""Tests for newest review pool resolution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from music_review.application.newest_review_pool import newest_reviews_for_update_rounds
from music_review.domain.models import Review
from music_review.io.update_batches import append_update_batch


def _review(
    review_id: int,
    *,
    first_seen_at: datetime | None = None,
) -> Review:
    return Review(
        review_id,
        f"https://example.com/{review_id}",
        f"A{review_id}",
        f"B{review_id}",
        "t",
        first_seen_at=first_seen_at,
    )


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

    reviews = [_review(1), _review(2), _review(3)]

    selected = newest_reviews_for_update_rounds(reviews, 1)

    assert [review.id for review in selected] == [3]


def test_newest_reviews_for_update_rounds_infers_missing_batch_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Missing batch history still returns only the latest first-seen cluster."""
    batches_path = tmp_path / "missing_update_batches.jsonl"
    monkeypatch.setattr(
        "music_review.application.newest_review_pool.update_batches_path",
        lambda: batches_path,
    )
    first_batch = datetime(2026, 6, 1, 10, tzinfo=UTC)
    second_batch = datetime(2026, 6, 8, 10, tzinfo=UTC)
    reviews = [
        _review(1, first_seen_at=first_batch),
        _review(2, first_seen_at=first_batch + timedelta(minutes=1)),
        _review(3, first_seen_at=second_batch),
        _review(4, first_seen_at=second_batch + timedelta(minutes=1)),
    ]

    selected = newest_reviews_for_update_rounds(reviews, 1)

    assert [review.id for review in selected] == [4, 3]
