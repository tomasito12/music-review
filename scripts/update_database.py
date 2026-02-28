#!/usr/bin/env python3
"""Update the full database: reviews.jsonl, metadata.jsonl, artist_genres.json."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_module(module: str, args: list[str]) -> bool:
    """Run a module with the given args. Return True on success."""
    cmd = [sys.executable, "-m", module] + args
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d", result.returncode)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update the full database: reviews, metadata, artist_genres.",
    )
    parser.add_argument(
        "--max-id",
        type=int,
        default=None,
        metavar="ID",
        help=(
            "Optional: stop scraper at this ID. If omitted, scraper stops automatically "
            "after 3 consecutive missing IDs."
        ),
    )
    parser.add_argument(
        "--reviews",
        default="data/reviews.jsonl",
        help="Path to reviews JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--metadata",
        default="data/metadata.jsonl",
        help="Path to metadata JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--artist-genres",
        default="data/artist_genres.json",
        help="Path to artist_genres.json (default: %(default)s).",
    )
    parser.add_argument(
        "--metadata-imputed",
        default="data/metadata_imputed.jsonl",
        help="Path to imputed metadata JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose scraper output.",
    )
    parser.add_argument(
        "--metadata-update",
        action="store_true",
        help="Refresh existing metadata entries (not just append new).",
    )
    parser.add_argument(
        "--skip-reviews",
        action="store_true",
        help="Skip the scraper step (only update metadata and artist_genres).",
    )
    args = parser.parse_args()

    verbose = ["-v"] if args.verbose else []

    if not args.skip_reviews:
        scraper_args = verbose + ["--output", args.reviews, "resume"]
        if args.max_id is not None:
            scraper_args.extend(["--max-id", str(args.max_id)])
        if not run_module("music_review.pipeline.scraper.cli", scraper_args):
            return 1

    fetch_args = [
        "--input",
        args.reviews,
        "--output",
        args.metadata,
    ]
    if args.metadata_update:
        fetch_args.append("--update")
    if not run_module(
        "music_review.pipeline.enrichment.fetch_metadata",
        fetch_args,
    ):
        return 1

    if not run_module(
        "music_review.pipeline.enrichment.artist_genres",
        [
            "--metadata",
            args.metadata,
            "--artist-profiles-output",
            args.artist_genres,
            "--imputed-metadata-output",
            args.metadata_imputed,
        ],
    ):
        return 1

    logger.info("Database update complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
