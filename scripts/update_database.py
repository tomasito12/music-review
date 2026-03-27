#!/usr/bin/env python3
"""Update the full database: reviews, metadata, imputation, and (by default) Chroma."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run_module(module: str, args: list[str]) -> bool:
    """Run a module with the given args. Return True on success."""
    cmd = [sys.executable, "-m", module, *args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d", result.returncode)
        return False
    return True


def _run_chroma_incremental(*, include_legacy: bool) -> int:
    """Chunk batch index by default; optional legacy whole-review collection."""
    from music_review.pipeline.retrieval.vector_store import (
        build_index,
        build_index_chunks_v1,
    )

    if include_legacy:
        try:
            added = build_index(recreate=False)
        except RuntimeError as e:
            if "OPENAI_API_KEY" in str(e):
                logger.error("%s", e)
                return 1
            raise
        logger.info(
            "Chroma legacy collection: indexed %d new review(s) (music_reviews).",
            added,
        )

    logger.info("Starting chunk batch indexing (music_reviews_chunks_v1) …")
    try:
        added_chunks = build_index_chunks_v1(recreate=False)
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            logger.error("%s", e)
            return 1
        raise
    logger.info(
        "Chroma chunk collection: added %d new chunk(s).",
        added_chunks,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Update reviews JSONL, MusicBrainz metadata, genre imputation, "
            "reference graph + stable communities (res 10) + "
            "album_community_affinities.jsonl, and by default incremental Chroma "
            "chunk index (OpenAI Batch API). "
            "Use --skip-graph-affinities or --skip-chroma to skip steps."
        ),
    )
    parser.add_argument(
        "--max-id",
        type=int,
        default=None,
        metavar="ID",
        help=(
            "Optional: stop scraper at this ID. "
            "If omitted, scraper stops automatically "
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
        "--metadata-min-review-id",
        type=int,
        default=None,
        metavar="ID",
        help=(
            "Pass to fetch_metadata: only request MusicBrainz for review id >= ID "
            "(incremental mode only; incompatible with --metadata-update). "
            "Useful after resume when only new high-numbered reviews matter."
        ),
    )
    parser.add_argument(
        "--skip-reviews",
        action="store_true",
        help="Skip the scraper step (only update metadata and artist_genres).",
    )
    parser.add_argument(
        "--skip-graph-affinities",
        action="store_true",
        help=(
            "Skip reference graph rebuild, community exports (res 10), and "
            "album_community_affinities.jsonl (faster if graph data is still valid)."
        ),
    )
    parser.add_argument(
        "--recluster-communities",
        action="store_true",
        help=(
            "Re-run Louvain on the full graph (new C00x community IDs). "
            "Invalidates existing community_genre_labels JSON — relabel communities "
            "afterwards. Default is incremental mode (stable IDs from "
            "community_memberships.jsonl)."
        ),
    )
    parser.add_argument(
        "--skip-chroma",
        action="store_true",
        help=("Skip vector indexing after the JSONL steps (no OpenAI / Chroma calls)."),
    )
    parser.add_argument(
        "--chroma-legacy",
        action="store_true",
        help=(
            "Also incrementally index the legacy whole-review Chroma collection "
            "(music_reviews). By default only the chunk collection is updated."
        ),
    )
    args = parser.parse_args()

    verbose = ["-v"] if args.verbose else []

    if not args.skip_reviews:
        scraper_args = [*verbose, "--output", args.reviews, "resume"]
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
    if args.metadata_min_review_id is not None:
        fetch_args.extend(
            ["--min-review-id", str(args.metadata_min_review_id)],
        )
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

    if not run_module(
        "music_review.pipeline.enrichment.reference_imputation",
        [
            "--imputed-metadata",
            args.metadata_imputed,
            "--reviews",
            args.reviews,
            "--artist-genres",
            args.artist_genres,
        ],
    ):
        return 1

    if args.skip_graph_affinities:
        logger.info(
            "Skipping reference graph + album_community_affinities "
            "(--skip-graph-affinities).",
        )
    else:
        mode = "Louvain recluster" if args.recluster_communities else "incremental"
        logger.info(
            "Rebuilding artist graph, exporting communities (res 10, %s), "
            "and album_community_affinities.jsonl …",
            mode,
        )
        graph_args = [
            "--reviews",
            args.reviews,
            "--export-communities",
            "10",
            "--export-album-affinities",
            "--communities-mode",
            "louvain" if args.recluster_communities else "incremental",
        ]
        if not run_module(
            "music_review.pipeline.retrieval.reference_graph_cli",
            graph_args,
        ):
            return 1

    if args.skip_graph_affinities:
        logger.info(
            "Database update complete (reviews + metadata + imputation; "
            "graph skipped).",
        )
    else:
        logger.info(
            "Database update complete (reviews + metadata + imputation + graph "
            "+ album_community_affinities).",
        )

    if args.skip_chroma:
        logger.info("Skipping Chroma (--skip-chroma).")
    elif not os.environ.get("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY not set; skipping Chroma. "
            "Set it in .env and re-run without --skip-chroma, or index manually.",
        )
    else:
        rc = _run_chroma_incremental(include_legacy=args.chroma_legacy)
        if rc != 0:
            return rc

    logger.info("Full update pipeline finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
