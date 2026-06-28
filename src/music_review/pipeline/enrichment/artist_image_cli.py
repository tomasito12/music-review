"""CLI spike for resolving artist images from Wikimedia Commons."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from music_review.application.artist_image_batch import (
    artist_lookup_from_review_metadata,
)
from music_review.application.artist_image_download import artist_image_download_enabled
from music_review.application.artist_image_models import ArtistImageRecord
from music_review.application.artist_image_resolver import resolve_artist_image
from music_review.application.artist_image_service import ArtistImageService
from music_review.config import resolve_data_path
from music_review.data_access.paths import (
    DATA_ARTIST_IMAGES,
    DATA_METADATA,
    artist_images_dir,
)
from music_review.io.jsonl import iter_jsonl_objects

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_MBIDS: tuple[tuple[str, str], ...] = (
    ("a74b1b7f-71a5-4011-9441-d0b5e4122711", "Radiohead"),
    ("b10bbbfc-cf9e-42e6-be17-eae9f4c4f4d4", "The Beatles"),
    ("6cab0dd8-ade3-4f48-ad96-2e3a792f0b13", "Björk"),
    ("8e99283e-4bdb-4fb6-92ab-4412e7700a3c", "The Notwist"),
    ("32931937-6d12-4734-a2de-9889d18de456", "Tocotronic"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve artist images via MusicBrainz, Wikidata, and Wikimedia Commons."
        ),
    )
    parser.add_argument("--mbid", help="MusicBrainz artist MBID.")
    parser.add_argument("--artist-name", help="Artist name used for search or display.")
    parser.add_argument(
        "--review-id",
        type=int,
        help="Resolve the artist for one review id via metadata JSONL.",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=Path(DATA_METADATA),
        help="Metadata JSONL used by --review-id (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DATA_ARTIST_IMAGES),
        help="JSONL cache path (default: %(default)s).",
    )
    parser.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="Resolve N artists from metadata.jsonl or built-in sample MBIDs.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(DATA_METADATA),
        help="Metadata JSONL used by --sample (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve images but do not write the JSONL cache.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore cached entries and resolve again.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="DEBUG logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for artist image resolution."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_path = resolve_data_path(args.output)
    targets = _resolve_targets(args)
    if not targets:
        logger.error("Provide --mbid, --artist-name, --review-id, or --sample N.")
        return 1

    service = ArtistImageService(
        cache_path=output_path,
        images_dir=artist_images_dir(),
        download_enabled=artist_image_download_enabled(),
    )

    ok_count = 0
    for artist_mbid, artist_name in targets:
        record = _lookup_target(
            service,
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            dry_run=args.dry_run,
            force=args.force,
            output_path=output_path,
        )
        _print_record(record)
        if record.status == "ok":
            ok_count += 1

    logger.info("Resolved %d/%d artist images successfully.", ok_count, len(targets))
    return 0 if ok_count > 0 else 1


def _lookup_target(
    service: ArtistImageService,
    *,
    artist_mbid: str,
    artist_name: str,
    dry_run: bool,
    force: bool,
    output_path: Path,
) -> ArtistImageRecord:
    """Resolve one CLI target and optionally persist it to the JSONL cache."""
    if dry_run:
        return resolve_artist_image(
            artist_mbid=artist_mbid or None,
            artist_name=artist_name or None,
        )

    if artist_mbid.strip():
        return service.lookup(
            artist_mbid,
            artist_name=artist_name or None,
            force=force,
        )

    return service.lookup(
        "",
        artist_name=artist_name,
        force=force,
    )


def _resolve_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Build the list of artists to resolve for this CLI invocation."""
    if args.sample is not None:
        return _sample_targets(resolve_data_path(args.metadata), args.sample)

    if args.review_id is not None:
        from music_review.io.jsonl import load_jsonl_as_map

        metadata = load_jsonl_as_map(
            resolve_data_path(args.reviews),
            id_key="review_id",
            log_errors=False,
        )
        artist_mbid, artist_name = artist_lookup_from_review_metadata(
            metadata,
            args.review_id,
        )
        if artist_mbid is None and not artist_name:
            logger.error("No metadata found for review id %s.", args.review_id)
            return []
        return [(artist_mbid or "", artist_name)]

    if args.mbid or args.artist_name:
        return [(args.mbid or "", args.artist_name or "")]

    return []


def _sample_targets(metadata_path: Path, count: int) -> list[tuple[str, str]]:
    """Pick sample artists from metadata or built-in fallback MBIDs."""
    from_metadata = _sample_from_metadata(metadata_path, count)
    if from_metadata:
        return from_metadata

    logger.warning(
        "No metadata sample available at %s; using built-in fallback MBIDs.",
        metadata_path,
    )
    return [(mbid, name) for mbid, name in DEFAULT_SAMPLE_MBIDS[: max(1, count)]]


def _sample_from_metadata(
    metadata_path: Path,
    count: int,
) -> list[tuple[str, str]]:
    """Return up to ``count`` unique artist MBIDs from metadata JSONL."""
    if not metadata_path.exists():
        return []

    seen: set[str] = set()
    samples: list[tuple[str, str]] = []
    for obj in iter_jsonl_objects(metadata_path, log_errors=False):
        artist_mbid = obj.get("artist_mbid")
        artist_name = obj.get("artist")
        if not isinstance(artist_mbid, str) or not artist_mbid.strip():
            continue
        if artist_mbid in seen:
            continue
        seen.add(artist_mbid)
        samples.append((artist_mbid, str(artist_name) if artist_name else artist_mbid))
        if len(samples) >= count:
            break
    return samples


def _print_record(record: object) -> None:
    """Print one resolved record as JSON for CLI inspection."""
    if hasattr(record, "to_dict"):
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(record)


if __name__ == "__main__":
    sys.exit(main())
