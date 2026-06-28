"""CLI for overnight artist image batch prefetch."""

from __future__ import annotations

import argparse
import logging
import sys
from os import environ
from pathlib import Path

from music_review.application.artist_image_batch import (
    ArtistImageQueue,
    artist_targets_from_metadata,
    run_artist_image_batch,
    split_targets_by_queue,
    write_batch_report,
)
from music_review.application.artist_image_download import artist_image_download_enabled
from music_review.application.artist_image_service import batch_artist_image_service
from music_review.config import resolve_data_path
from music_review.data_access.paths import (
    DATA_ARTIST_GENRES,
    DATA_METADATA,
    DATA_METADATA_IMPUTED,
)

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 300


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prefetch artist images into data/artist_images.jsonl with strict "
            "confidence scoring."
        ),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(DATA_METADATA),
        help="Metadata JSONL used to enumerate artists (default: %(default)s).",
    )
    parser.add_argument(
        "--artist-genres",
        type=Path,
        default=Path(DATA_ARTIST_GENRES),
        help="Artist genres JSON used for validation hints (default: %(default)s).",
    )
    parser.add_argument(
        "--missing-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip artists with fresh ok/not_found cache entries.",
    )
    parser.add_argument(
        "--revalidate",
        action="store_true",
        help="Re-score cached ok entries and downgrade failures.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cache and resolve every selected artist again.",
    )
    parser.add_argument(
        "--queue",
        choices=("all", "mbid", "name"),
        default="all",
        help="Select MBID-backed, name-only, or all artist queues.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Maximum artists to process in this run (ignored with --all).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="process_all",
        help="Process every selected artist; ignore --limit.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N selected artists.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download JPG thumbnails into data/artist_images/.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON report path for batch counters.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one artist image batch slice."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.download:
        environ["ARTIST_IMAGE_DOWNLOAD"] = "true"

    metadata_path = resolve_data_path(args.metadata)
    if args.metadata == Path(DATA_METADATA):
        imputed_path = resolve_data_path(Path(DATA_METADATA_IMPUTED))
        if imputed_path.is_file():
            metadata_path = imputed_path

    genres_path = resolve_data_path(args.artist_genres)
    targets = artist_targets_from_metadata(
        metadata_path,
        artist_genres_path=genres_path if genres_path.is_file() else None,
    )
    queue: ArtistImageQueue = args.queue
    selected = split_targets_by_queue(targets, queue=queue)
    if not selected:
        logger.info("No artist targets found for queue=%s.", queue)
        return 0

    if args.process_all:
        logger.info(
            "Processing all %d artist target(s) (offset=%d, queue=%s).",
            max(0, len(selected) - max(0, args.offset)),
            max(0, args.offset),
            queue,
        )

    service = batch_artist_image_service()
    if args.download and not artist_image_download_enabled():
        logger.warning("Download flag set but ARTIST_IMAGE_DOWNLOAD is still false.")
    service.download_enabled = artist_image_download_enabled()

    report = run_artist_image_batch(
        service,
        selected,
        limit=max(1, args.limit),
        offset=max(0, args.offset),
        missing_only=args.missing_only,
        force=args.force,
        revalidate=args.revalidate,
        process_all=args.process_all,
    )
    if args.report is not None:
        write_batch_report(report, resolve_data_path(args.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
