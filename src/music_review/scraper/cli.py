# src/music_review/scraper/cli.py

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable

from music_review.scraper.client import (
    RateLimiter,
    ScraperClient,
    iter_review_html,
)
from music_review.scraper.parser import parse_review
from music_review.scraper.storage import append_review, load_existing_ids

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the music-review scraper CLI."""
    args = _build_arg_parser().parse_args(argv)

    _configure_logging(verbose=args.verbose)

    output_path = Path(args.output)

    try:
        if args.command == "run":
            _cmd_run(
                start_id=args.start_id,
                end_id=args.end_id,
                output_path=output_path,
                max_rps=args.max_rps,
            )
        elif args.command == "full":
            _cmd_run(
                start_id=1,
                end_id=args.max_id,
                output_path=output_path,
                max_rps=args.max_rps,
            )
        elif args.command == "resume":
            _cmd_resume(
                max_id=args.max_id,
                output_path=output_path,
                max_rps=args.max_rps,
            )
        else:
            msg = f"Unknown command: {args.command}"
            raise ValueError(msg)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Exiting.")
        sys.exit(1)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-review-scraper",
        description="Scrape plattentests.de reviews into a JSONL file.",
    )

    parser.add_argument(
        "--output",
        default="data/reviews.jsonl",
        help="Path to output JSONL file (default: %(default)s).",
    )
    parser.add_argument(
        "--max-rps",
        type=float,
        default=2.5,
        help="Maximum requests per second (default: %(default)s).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Sub-command to run.",
    )

    # run: explicit start/end
    run_parser = subparsers.add_parser(
        "run",
        help="Scrape a specific ID range.",
    )
    run_parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="First review ID to scrape (default: %(default)s).",
    )
    run_parser.add_argument(
        "--end-id",
        type=int,
        required=True,
        help="Last review ID (inclusive) to scrape.",
    )

    # full: from 1..max_id
    full_parser = subparsers.add_parser(
        "full",
        help="Scrape from ID 1 up to max-id.",
    )
    full_parser.add_argument(
        "--max-id",
        type=int,
        required=True,
        help="Maximum review ID currently existing on the site.",
    )

    # resume: continue after highest existing ID in the output file
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume scraping after the highest ID in the output file.",
    )
    resume_parser.add_argument(
        "--max-id",
        type=int,
        required=True,
        help="Maximum review ID currently existing on the site.",
    )

    return parser


def _configure_logging(*, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _cmd_run(
    *,
    start_id: int,
    end_id: int,
    output_path: Path,
    max_rps: float,
) -> None:
    if start_id < 1:
        msg = "start_id must be >= 1."
        raise ValueError(msg)
    if end_id < start_id:
        msg = "end_id must be >= start_id."
        raise ValueError(msg)

    ids: Iterable[int] = range(start_id, end_id + 1)
    logger.info("Scraping IDs from %s to %s into %s.", start_id, end_id, output_path)

    rate_limiter = RateLimiter(max_per_second=max_rps)

    with ScraperClient() as client:
        processed = 0
        for review_id, html in iter_review_html(client, ids, rate_limiter=rate_limiter):
            if html is None:
                continue

            review = parse_review(review_id, html)
            if review is None:
                continue

            append_review(output_path, review)
            processed += 1

            if processed % 50 == 0:
                logger.info("Processed %s reviews so far.", processed)

    logger.info("Done. Processed %s reviews.", processed)


def _cmd_resume(
    *,
    max_id: int,
    output_path: Path,
    max_rps: float,
) -> None:
    if max_id < 1:
        msg = "max_id must be >= 1."
        raise ValueError(msg)

    if not output_path.exists():
        logger.info(
            "Output file %s does not exist yet. Falling back to full scrape.",
            output_path,
        )
        _cmd_run(
            start_id=1,
            end_id=max_id,
            output_path=output_path,
            max_rps=max_rps,
        )
        return

    existing_ids = load_existing_ids(output_path)
    if not existing_ids:
        logger.info(
            "Output file %s exists but contains no reviews. Falling back to full scrape.",
            output_path,
        )
        _cmd_run(
            start_id=1,
            end_id=max_id,
            output_path=output_path,
            max_rps=max_rps,
        )
        return

    start_id = max(existing_ids) + 1
    if start_id > max_id:
        logger.info(
            "Nothing to resume: highest ID in %s is %s, max-id is %s.",
            output_path,
            start_id - 1,
            max_id,
        )
        return

    logger.info(
        "Resuming scrape from ID %s up to %s (existing IDs: %s entries).",
        start_id,
        max_id,
        len(existing_ids),
    )
    _cmd_run(
        start_id=start_id,
        end_id=max_id,
        output_path=output_path,
        max_rps=max_rps,
    )


if __name__ == "__main__":
    main()
