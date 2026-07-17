"""Select newest reviews by stored scrape batches or review-id fallback."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal

from music_review.domain.models import Review
from music_review.io.backfill_update_batches import cluster_review_ids_by_first_seen
from music_review.io.update_batches import (
    UpdateBatch,
    has_update_batch_history,
    review_ids_for_last_n_batches,
)

REVIEWS_PER_ROUND_FALLBACK = 20
MAX_UPDATE_ROUNDS = 20
NewestReviewPoolMode = Literal[
    "update_batches",
    "inferred_first_seen_at",
    "review_count_fallback",
]
logger = logging.getLogger(__name__)


def _newest_review_id(reviews: Sequence[Review]) -> int | None:
    """Return the highest review id in the loaded corpus."""
    if not reviews:
        return None
    return max(review.id for review in reviews)


def _newest_batch_review_id(batches: Sequence[UpdateBatch]) -> int | None:
    """Return the highest review id covered by stored update batches."""
    review_ids = [review_id for batch in batches for review_id in batch.review_ids]
    if not review_ids:
        return None
    return max(review_ids)


def _fallback_reviews(
    reviews: Sequence[Review],
    rounds: int,
    *,
    reviews_per_round_fallback: int,
) -> list[Review]:
    """Return newest reviews by id when exact update batches are unavailable."""
    fallback_count = max(1, rounds * reviews_per_round_fallback)
    return sorted(reviews, key=lambda review: review.id, reverse=True)[:fallback_count]


def _infer_batches_from_first_seen(
    reviews: Sequence[Review],
) -> tuple[UpdateBatch, ...]:
    """Infer update batches from review first-seen timestamps."""
    reviews_with_seen_at = []
    for review in reviews:
        if review.first_seen_at is not None:
            reviews_with_seen_at.append((review.id, review.first_seen_at))
    return cluster_review_ids_by_first_seen(reviews_with_seen_at)


def _reviews_for_batch_ids(
    reviews: Sequence[Review],
    batch_ids: frozenset[int],
) -> list[Review]:
    """Return reviews matching batch ids, newest id first."""
    selected = [review for review in reviews if review.id in batch_ids]
    selected.sort(key=lambda review: review.id, reverse=True)
    return selected


def select_reviews_for_update_rounds(
    reviews: Sequence[Review],
    batches: Sequence[UpdateBatch],
    update_rounds: int,
    *,
    reviews_per_round_fallback: int = REVIEWS_PER_ROUND_FALLBACK,
) -> tuple[list[Review], NewestReviewPoolMode]:
    """Return reviews for the last N scrape batches, or a count-based fallback."""
    rounds = max(1, min(int(update_rounds), MAX_UPDATE_ROUNDS))
    use_inferred_batches = not has_update_batch_history(batches)

    if has_update_batch_history(batches):
        newest_review_id = _newest_review_id(reviews)
        newest_batch_id = _newest_batch_review_id(batches)
        if (
            newest_review_id is None
            or newest_batch_id is None
            or newest_batch_id >= newest_review_id
        ):
            batch_ids = review_ids_for_last_n_batches(batches, rounds)
            selected = _reviews_for_batch_ids(reviews, batch_ids)
            if selected:
                return selected, "update_batches"
            logger.warning(
                "Update batch history exists but did not match loaded reviews; "
                "falling back to first_seen_at inference.",
            )
            use_inferred_batches = True
        else:
            logger.warning(
                "Update batch history is stale "
                "(latest batch review id %s < latest corpus review id %s); "
                "falling back to first_seen_at inference.",
                newest_batch_id,
                newest_review_id,
            )
            use_inferred_batches = True

    if use_inferred_batches:
        inferred_batches = _infer_batches_from_first_seen(reviews)
        batch_ids = review_ids_for_last_n_batches(inferred_batches, rounds)
        selected = _reviews_for_batch_ids(reviews, batch_ids)
        if selected:
            return selected, "inferred_first_seen_at"
        logger.warning(
            "No usable update batches could be inferred from first_seen_at; "
            "falling back to newest review ids.",
        )

    selected = _fallback_reviews(
        reviews,
        rounds,
        reviews_per_round_fallback=reviews_per_round_fallback,
    )
    return selected, "review_count_fallback"
