# music_review/pipeline/scraper/cli.py

"""Thin CLI wrapper for the scraper service."""

from __future__ import annotations

import argparse
import logging
import sys
from enum import StrEnum
from pathlib import Path

from music_review.config import resolve_data_path
from music_review.pipeline.scraper.service import scrape_ids, scrape_until_gap
from music_review.pipeline.scraper.storage import load_existing_ids

logger = logging.getLogger(__name__)


class ExistingMode(StrEnum):
    ADD = "add"
    UPDATE = "update"


def main(argv: list[str] | None = None) -> None:
    """Entry point for the music-review scraper CLI."""
    args = _build_arg_parser().parse_args(argv)

    _configure_logging(verbose=args.verbose)

    output_path = resolve_data_path(args.output)
    existing_mode = ExistingMode(args.existing)

    try:
        if args.command == "run":
            _cmd_run(
                start_id=args.start_id,
                end_id=args.end_id,
                output_path=output_path,
                max_rps=args.max_rps,
                existing_mode=existing_mode,
            )
        elif args.command == "full":
            _cmd_run(
                start_id=1,
                end_id=args.max_id,
                output_path=output_path,
                max_rps=args.max_rps,
                existing_mode=existing_mode,
            )
        elif args.command == "resume":
            _cmd_resume(
                max_id=args.max_id,
                output_path=output_path,
                max_rps=args.max_rps,
                existing_mode=existing_mode,
                stop_after_n_empty=args.stop_after_n_empty,
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
    parser.add_argument(
        "--existing",
        choices=[m.value for m in ExistingMode],
        default=ExistingMode.ADD.value,
        help=(
            "How to handle IDs that already exist in the corpus: "
            "'add' (default) only adds new IDs, 'update' overwrites existing IDs."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Sub-command to run.",
    )

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

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume scraping after the highest ID in the output file.",
    )
    resume_parser.add_argument(
        "--max-id",
        type=int,
        default=None,
        help=(
            "Optional: stop at this ID. If omitted, scraping stops after "
            "--stop-after-n-empty consecutive missing IDs (default: 3)."
        ),
    )
    resume_parser.add_argument(
        "--stop-after-n-empty",
        type=int,
        default=3,
        metavar="N",
        help=(
            "When --max-id is not set, stop after N consecutive missing IDs "
            "(default: %(default)s)."
        ),
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
    existing_mode: ExistingMode,
) -> None:
    if start_id < 1:
        msg = "start_id must be >= 1."
        raise ValueError(msg)
    if end_id < start_id:
        msg = "end_id must be >= start_id."
        raise ValueError(msg)

    all_ids: list[int] = list(range(start_id, end_id + 1))
    update_mode = existing_mode is ExistingMode.UPDATE

    if existing_mode is ExistingMode.ADD and output_path.exists():
        existing_ids = load_existing_ids(output_path)
        skip = set(all_ids) & existing_ids
        ids = [i for i in all_ids if i not in existing_ids]
        if skip:
            logger.info(
                "Mode 'add': skipping %s IDs that already exist in %s.",
                len(skip),
                output_path,
            )
    else:
        ids = all_ids

    logger.info(
        "Scraping IDs from %s to %s into %s (mode=%s).",
        start_id,
        end_id,
        output_path,
        existing_mode.value,
    )

    scrape_ids(
        ids,
        output_path=output_path,
        max_rps=max_rps,
        update_mode=update_mode,
    )


def _cmd_resume(
    *,
    max_id: int | None,
    output_path: Path,
    max_rps: float,
    existing_mode: ExistingMode,
    stop_after_n_empty: int = 3,
) -> None:
    if max_id is not None and max_id < 1:
        msg = "max_id must be >= 1 when provided."
        raise ValueError(msg)

    update_mode = existing_mode is ExistingMode.UPDATE

    start_id = _resolve_resume_start_id(output_path)

    if start_id is None:
        if max_id is None:
            logger.info(
                "Output file %s does not exist or is empty. Starting from ID 1; "
                "will stop after %s consecutive missing IDs.",
                output_path,
                stop_after_n_empty,
            )
            scrape_until_gap(
                1,
                output_path=output_path,
                max_rps=max_rps,
                update_mode=update_mode,
                stop_after_n_empty=stop_after_n_empty,
            )
        else:
            logger.info(
                "Output file %s does not exist or is empty. "
                "Falling back to full scrape.",
                output_path,
            )
            _cmd_run(
                start_id=1,
                end_id=max_id,
                output_path=output_path,
                max_rps=max_rps,
                existing_mode=existing_mode,
            )
        return

    if max_id is None:
        logger.info(
            "Resuming from ID %s. Will stop after %s consecutive missing IDs.",
            start_id,
            stop_after_n_empty,
        )
        scrape_until_gap(
            start_id,
            output_path=output_path,
            max_rps=max_rps,
            update_mode=update_mode,
            stop_after_n_empty=stop_after_n_empty,
        )
        return

    if start_id > max_id:
        logger.info(
            "Nothing to resume: highest ID in %s is %s, max-id is %s.",
            output_path,
            start_id - 1,
            max_id,
        )
        return

    logger.info(
        "Resuming scrape from ID %s up to %s (mode=%s).",
        start_id,
        max_id,
        existing_mode.value,
    )
    _cmd_run(
        start_id=start_id,
        end_id=max_id,
        output_path=output_path,
        max_rps=max_rps,
        existing_mode=existing_mode,
    )


def _resolve_resume_start_id(output_path: Path) -> int | None:
    """Determine the start ID for resume, or None if no valid corpus exists."""
    if not output_path.exists():
        return None
    existing_ids = load_existing_ids(output_path)
    if not existing_ids:
        return None
    return max(existing_ids) + 1


if __name__ == "__main__":
    # python -m music_review.pipeline.scraper.cli -v run --start-id 1 --end-id 100
    main()
