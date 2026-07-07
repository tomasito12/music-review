"""Resolve newest-review pools for Aktuell and playlist exports."""

from __future__ import annotations

from collections.abc import Sequence

from music_review.application.update_batch_selection import (
    NewestReviewPoolMode,
    select_reviews_for_update_rounds,
)
from music_review.data_access.paths import update_batches_path
from music_review.domain.models import Review
from music_review.io.update_batches import load_update_batches


def newest_reviews_for_update_rounds(
    reviews: Sequence[Review],
    update_rounds: int,
) -> list[Review]:
    """Return the review pool for one Aktuell update-round selection."""
    selected, _mode = resolve_newest_review_pool(reviews, update_rounds)
    return selected


def resolve_newest_review_pool(
    reviews: Sequence[Review],
    update_rounds: int,
) -> tuple[list[Review], NewestReviewPoolMode]:
    """Return the newest-review pool and whether batch history was used."""
    batches = load_update_batches(update_batches_path())
    return select_reviews_for_update_rounds(
        reviews,
        batches,
        update_rounds,
    )
