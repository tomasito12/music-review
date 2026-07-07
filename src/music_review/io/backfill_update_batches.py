"""Rebuild update batch history from review first_seen_at timestamps."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from music_review.data_access.paths import DATA_REVIEWS, DATA_UPDATE_BATCHES
from music_review.io.jsonl import write_jsonl
from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.io.update_batches import (
    UpdateBatch,
    load_update_batches,
    update_batch_to_raw,
)

logger = logging.getLogger(__name__)

DEFAULT_CLUSTER_GAP = timedelta(hours=3)


def cluster_review_ids_by_first_seen(
    reviews: Sequence[tuple[int, datetime]],
    *,
    cluster_gap: timedelta = DEFAULT_CLUSTER_GAP,
) -> tuple[UpdateBatch, ...]:
    """Group reviews into scrape batches using first_seen_at proximity."""
    if not reviews:
        return ()

    ordered = sorted(reviews, key=lambda item: (item[1], item[0]))
    batches: list[UpdateBatch] = []
    current_ids: list[int] = []
    cluster_start: datetime | None = None
    cluster_end: datetime | None = None

    def flush_cluster() -> None:
        nonlocal current_ids, cluster_start, cluster_end
        if not current_ids or cluster_end is None:
            current_ids = []
            cluster_start = None
            cluster_end = None
            return
        batches.append(
            UpdateBatch(
                run_at=cluster_end.astimezone(UTC),
                review_ids=tuple(current_ids),
            ),
        )
        current_ids = []
        cluster_start = None
        cluster_end = None

    for review_id, seen_at in ordered:
        seen_at = seen_at.astimezone(UTC)
        if cluster_start is None:
            cluster_start = seen_at
            cluster_end = seen_at
            current_ids = [review_id]
            continue

        if seen_at - cluster_start <= cluster_gap:
            current_ids.append(review_id)
            cluster_end = seen_at
            continue

        flush_cluster()
        cluster_start = seen_at
        cluster_end = seen_at
        current_ids = [review_id]

    flush_cluster()
    return tuple(batches)


def backfill_update_batches_from_reviews(
    reviews_path: str | Path,
    *,
    output_path: str | Path,
    cluster_gap: timedelta = DEFAULT_CLUSTER_GAP,
    merge_existing: bool = True,
    dry_run: bool = False,
) -> tuple[UpdateBatch, ...]:
    """Write scrape batches inferred from review first_seen_at timestamps."""
    reviews_with_seen_at: list[tuple[int, datetime]] = []
    missing_first_seen = 0
    for review in load_reviews_from_jsonl(reviews_path):
        if review.first_seen_at is None:
            missing_first_seen += 1
            continue
        reviews_with_seen_at.append((review.id, review.first_seen_at))

    inferred = cluster_review_ids_by_first_seen(
        reviews_with_seen_at,
        cluster_gap=cluster_gap,
    )
    if missing_first_seen:
        logger.warning(
            "Skipped %s reviews without first_seen_at during backfill.",
            missing_first_seen,
        )

    output = Path(output_path)
    if merge_existing and output.is_file():
        existing = load_update_batches(output)
        merged: dict[tuple[int, ...], UpdateBatch] = {
            batch.review_ids: batch for batch in existing
        }
        for batch in inferred:
            merged.setdefault(batch.review_ids, batch)
        batches = tuple(sorted(merged.values(), key=lambda item: item.run_at))
    else:
        batches = inferred

    if dry_run:
        logger.info(
            "Dry run: would write %s update batches to %s.",
            len(batches),
            output,
        )
        return batches

    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, [update_batch_to_raw(batch) for batch in batches])
    logger.info("Wrote %s update batches to %s.", len(batches), output)
    return batches


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild data/update_batches.jsonl from review first_seen_at timestamps."
        ),
    )
    parser.add_argument("--reviews", default=DATA_REVIEWS)
    parser.add_argument("--output", default=DATA_UPDATE_BATCHES)
    parser.add_argument(
        "--cluster-gap-hours",
        type=float,
        default=DEFAULT_CLUSTER_GAP.total_seconds() / 3600,
        help="Maximum span for one inferred scrape batch (default: 3 hours).",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the output file instead of merging with existing batches.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for update-batch backfill."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    backfill_update_batches_from_reviews(
        args.reviews,
        output_path=args.output,
        cluster_gap=timedelta(hours=args.cluster_gap_hours),
        merge_existing=not args.replace,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
