"""Tests for newest-review pool selection by scrape batches."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from music_review.application.update_batch_selection import (
    REVIEWS_PER_ROUND_FALLBACK,
    select_reviews_for_update_rounds,
)
from music_review.domain.models import Review
from music_review.io.update_batches import UpdateBatch


def _review(
    review_id: int,
    *,
    first_seen_at: datetime | None = None,
) -> Review:
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=f"Artist {review_id}",
        album=f"Album {review_id}",
        text="text",
        first_seen_at=first_seen_at,
    )


def _review_batch(
    review_ids: range,
    *,
    start: datetime,
) -> list[Review]:
    """Build reviews with first-seen timestamps close enough for one batch."""
    return [
        _review(review_id, first_seen_at=start + timedelta(minutes=offset))
        for offset, review_id in enumerate(review_ids)
    ]


def test_select_reviews_for_update_rounds_uses_batch_history() -> None:
    """When batches exist, only ids from the last N runs are returned."""
    reviews = [_review(review_id) for review_id in range(1, 11)]
    batches = (
        UpdateBatch(datetime(2026, 6, 1, tzinfo=UTC), (8, 9)),
        UpdateBatch(datetime(2026, 6, 2, tzinfo=UTC), (10,)),
    )

    selected, mode = select_reviews_for_update_rounds(reviews, batches, 1)

    assert mode == "update_batches"
    assert [review.id for review in selected] == [10]


def test_select_reviews_for_update_rounds_ignores_stale_batch_history() -> None:
    """A stale batch file must not hide newer reviews already in the corpus."""
    reviews = [
        *_review_batch(
            range(1, 11),
            start=datetime(2026, 6, 1, 10, tzinfo=UTC),
        ),
        *_review_batch(
            range(11, 16),
            start=datetime(2026, 6, 8, 10, tzinfo=UTC),
        ),
    ]
    batches = (
        UpdateBatch(datetime(2026, 6, 1, tzinfo=UTC), (8, 9)),
        UpdateBatch(datetime(2026, 6, 2, tzinfo=UTC), (10,)),
    )

    selected, mode = select_reviews_for_update_rounds(reviews, batches, 1)

    assert mode == "inferred_first_seen_at"
    assert [review.id for review in selected] == [15, 14, 13, 12, 11]


def test_select_reviews_for_update_rounds_falls_back_when_batch_ids_are_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Batch ids absent from the corpus fall back to inferred batches."""
    reviews = _review_batch(
        range(1, 6),
        start=datetime(2026, 6, 1, 10, tzinfo=UTC),
    )
    batches = (UpdateBatch(datetime(2026, 6, 1, tzinfo=UTC), (99,)),)

    selected, mode = select_reviews_for_update_rounds(reviews, batches, 1)

    assert mode == "inferred_first_seen_at"
    assert [review.id for review in selected] == [5, 4, 3, 2, 1]
    assert "did not match loaded reviews" in caplog.text


def test_select_reviews_for_update_rounds_uses_inferred_batches_without_history() -> (
    None
):
    """Without batch history, first_seen_at still preserves update rounds."""
    reviews = [
        *_review_batch(
            range(1, 11),
            start=datetime(2026, 6, 1, 10, tzinfo=UTC),
        ),
        *_review_batch(
            range(11, 16),
            start=datetime(2026, 6, 8, 10, tzinfo=UTC),
        ),
    ]

    selected, mode = select_reviews_for_update_rounds(reviews, (), 1)

    assert mode == "inferred_first_seen_at"
    assert [review.id for review in selected] == [15, 14, 13, 12, 11]


def test_select_reviews_for_update_rounds_falls_back_to_review_count() -> None:
    """Without batch history or first_seen_at, use the 20-per-round fallback."""
    reviews = [_review(review_id) for review_id in range(1, 51)]

    selected, mode = select_reviews_for_update_rounds(reviews, (), 1)

    assert mode == "review_count_fallback"
    assert len(selected) == REVIEWS_PER_ROUND_FALLBACK
    assert selected[0].id == 50
