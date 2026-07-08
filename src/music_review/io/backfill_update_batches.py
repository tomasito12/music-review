"""Rebuild update batch history from review first_seen_at timestamps."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from music_review.data_access.paths import DATA_REVIEWS, DATA_UPDATE_BATCHES
from music_review.io.jsonl import write_jsonl
from music_review.io.reviews_jsonl import (
    load_reviews_from_jsonl,
)
from music_review.io.update_batches import (
    UpdateBatch,
    append_update_batch,
    load_update_batches,
    update_batch_to_raw,
)

logger = logging.getLogger(__name__)

DEFAULT_CLUSTER_GAP = timedelta(hours=3)
_HOURLY_LOG_BATCH_RE = re.compile(
    r"Found (\d+) new reviews \((\d+)-(\d+)\)\. Continuing with enrichment\.",
)
_HOURLY_LOG_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} [\d:,]+) .*Found (\d+) new reviews \((\d+)-(\d+)\)\."
    r" Continuing with enrichment\.",
)


def _parse_log_timestamp(value: str) -> datetime:
    """Parse a production log timestamp into UTC."""
    normalized = value.replace(",", ".", 1)
    try:
        parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    return parsed.replace(tzinfo=UTC)


def review_ids_in_inclusive_range(
    min_review_id: int,
    max_review_id: int,
    *,
    known_review_ids: frozenset[int] | None = None,
) -> tuple[int, ...]:
    """Return review ids in a closed interval, optionally filtered to the corpus."""
    if min_review_id > max_review_id:
        return ()
    candidate_ids = range(min_review_id, max_review_id + 1)
    if known_review_ids is None:
        return tuple(candidate_ids)
    return tuple(
        review_id for review_id in candidate_ids if review_id in known_review_ids
    )


def parse_batches_from_hourly_log(
    log_path: str | Path,
    *,
    known_review_ids: frozenset[int] | None = None,
) -> tuple[UpdateBatch, ...]:
    """Rebuild scrape batches from hourly production update log lines."""
    file_path = Path(log_path)
    if not file_path.is_file():
        logger.warning("Hourly log file not found: %s", file_path)
        return ()

    batches: list[UpdateBatch] = []
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _HOURLY_LOG_LINE_RE.match(line.strip())
        if match is None:
            continue
        run_at = _parse_log_timestamp(match.group(1))
        _count = int(match.group(2))
        min_id = int(match.group(3))
        max_id = int(match.group(4))
        review_ids = review_ids_in_inclusive_range(
            min_id,
            max_id,
            known_review_ids=known_review_ids,
        )
        if not review_ids:
            continue
        batches.append(UpdateBatch(run_at=run_at, review_ids=review_ids))

    if batches:
        return tuple(batches)

    for match in _HOURLY_LOG_BATCH_RE.finditer(file_path.read_text(encoding="utf-8")):
        _count = int(match.group(1))
        min_id = int(match.group(2))
        max_id = int(match.group(3))
        review_ids = review_ids_in_inclusive_range(
            min_id,
            max_id,
            known_review_ids=known_review_ids,
        )
        if not review_ids:
            continue
        batches.append(
            UpdateBatch(
                run_at=datetime.now(UTC),
                review_ids=review_ids,
            ),
        )
    return tuple(batches)


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


def backfill_update_batches_from_hourly_log(
    log_path: str | Path,
    *,
    reviews_path: str | Path,
    output_path: str | Path,
    merge_existing: bool = True,
    dry_run: bool = False,
) -> tuple[UpdateBatch, ...]:
    """Write scrape batches parsed from production hourly update logs."""
    reviews_file = Path(reviews_path)
    known_review_ids = frozenset(
        review.id for review in load_reviews_from_jsonl(reviews_file)
    )
    inferred = parse_batches_from_hourly_log(
        log_path,
        known_review_ids=known_review_ids,
    )
    logger.info(
        "Parsed %s update batches from hourly log %s.",
        len(inferred),
        log_path,
    )
    return _write_merged_batches(
        inferred,
        output_path=output_path,
        merge_existing=merge_existing,
        dry_run=dry_run,
    )


def _write_merged_batches(
    inferred: Sequence[UpdateBatch],
    *,
    output_path: str | Path,
    merge_existing: bool,
    dry_run: bool,
) -> tuple[UpdateBatch, ...]:
    """Merge inferred batches with any existing file and optionally write them."""
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
        batches = tuple(inferred)

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


def append_latest_batch_from_hourly_log(
    log_path: str | Path,
    *,
    reviews_path: str | Path = DATA_REVIEWS,
    output_path: str | Path = DATA_UPDATE_BATCHES,
    dry_run: bool = False,
) -> UpdateBatch | None:
    """Append only the most recent scrape batch found in the hourly log."""
    batches = parse_batches_from_hourly_log(
        log_path,
        known_review_ids=frozenset(
            review.id for review in load_reviews_from_jsonl(reviews_path)
        ),
    )
    if not batches:
        return None
    latest = batches[-1]
    if dry_run:
        logger.info(
            "Dry run: would append latest batch with %s reviews at %s.",
            latest.count,
            latest.run_at.isoformat(),
        )
        return latest
    return append_update_batch(
        latest.review_ids,
        path=output_path,
        run_at=latest.run_at,
    )


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

    return _write_merged_batches(
        inferred,
        output_path=output_path,
        merge_existing=merge_existing,
        dry_run=dry_run,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild data/update_batches.jsonl from first_seen_at timestamps "
            "or hourly production logs."
        ),
    )
    parser.add_argument("--reviews", default=DATA_REVIEWS)
    parser.add_argument("--output", default=DATA_UPDATE_BATCHES)
    parser.add_argument(
        "--hourly-log",
        default=None,
        metavar="PATH",
        help=("Parse batches from logs/hourly-update.log instead of first_seen_at."),
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="With --hourly-log, append only the newest scrape batch.",
    )
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
    if args.hourly_log:
        if args.latest_only:
            append_latest_batch_from_hourly_log(
                args.hourly_log,
                reviews_path=args.reviews,
                output_path=args.output,
                dry_run=args.dry_run,
            )
        else:
            backfill_update_batches_from_hourly_log(
                args.hourly_log,
                reviews_path=args.reviews,
                output_path=args.output,
                merge_existing=not args.replace,
                dry_run=args.dry_run,
            )
        return 0

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
