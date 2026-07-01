"""Resolve newest-review pools for Aktuell and playlist exports."""

from __future__ import annotations

from collections.abc import Sequence

from music_review.application.update_batch_selection import (
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
    batches = load_update_batches(update_batches_path())
    selected, _mode = select_reviews_for_update_rounds(
        reviews,
        batches,
        update_rounds,
    )
    return selected
