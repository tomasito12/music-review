"""Select newest reviews by stored scrape batches or review-id fallback."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from music_review.domain.models import Review
from music_review.io.update_batches import (
    UpdateBatch,
    has_update_batch_history,
    review_ids_for_last_n_batches,
)

REVIEWS_PER_ROUND_FALLBACK = 20
MAX_UPDATE_ROUNDS = 20
NewestReviewPoolMode = Literal["update_batches", "review_count_fallback"]


def select_reviews_for_update_rounds(
    reviews: Sequence[Review],
    batches: Sequence[UpdateBatch],
    update_rounds: int,
    *,
    reviews_per_round_fallback: int = REVIEWS_PER_ROUND_FALLBACK,
) -> tuple[list[Review], NewestReviewPoolMode]:
    """Return reviews for the last N scrape batches, or a count-based fallback."""
    rounds = max(1, min(int(update_rounds), MAX_UPDATE_ROUNDS))

    if has_update_batch_history(batches):
        batch_ids = review_ids_for_last_n_batches(batches, rounds)
        if batch_ids:
            selected = [review for review in reviews if review.id in batch_ids]
            selected.sort(key=lambda review: review.id, reverse=True)
            return selected, "update_batches"

    fallback_count = max(1, rounds * reviews_per_round_fallback)
    selected = sorted(reviews, key=lambda review: review.id, reverse=True)[
        :fallback_count
    ]
    return selected, "review_count_fallback"
