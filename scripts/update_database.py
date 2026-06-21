#!/usr/bin/env python3
"""Update the full database: reviews, metadata, imputation, graph, and DQ."""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys

# Load ``.env`` before orchestration checks ``OPENAI_API_KEY``.
with contextlib.suppress(ImportError):
    import music_review.config  # noqa: F401 — side effect: ``load_dotenv``

from music_review.data_access.paths import (
    DATA_ARTIST_GENRES,
    DATA_METADATA,
    DATA_METADATA_IMPUTED,
    DATA_PIPELINE_HEALTH_REPORT,
    DATA_REVIEWS,
)
from music_review.pipeline.orchestration import (
    pipeline_config_from_namespace,
    run_pipeline_update,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Update reviews JSONL, MusicBrainz metadata, genre imputation, "
            "reference graph + stable communities (res 10) + "
            "album_community_affinities.jsonl. "
            "Use --skip-graph-affinities to skip graph steps."
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
        default=DATA_REVIEWS,
        help="Path to reviews JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--metadata",
        default=DATA_METADATA,
        help="Path to metadata JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--artist-genres",
        default=DATA_ARTIST_GENRES,
        help="Path to artist_genres.json (default: %(default)s).",
    )
    parser.add_argument(
        "--metadata-imputed",
        default=DATA_METADATA_IMPUTED,
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
        "--skip-dq",
        action="store_true",
        help="Skip data-quality checks and health report after the pipeline.",
    )
    parser.add_argument(
        "--dq-strict",
        action="store_true",
        help=("Fail the run (exit 1) if any DQ warning is present, not only errors."),
    )
    parser.add_argument(
        "--dq-output",
        default=DATA_PIPELINE_HEALTH_REPORT,
        help="Path for the DQ JSON report (default: %(default)s).",
    )
    args = parser.parse_args()
    config = pipeline_config_from_namespace(args)

    if config.skip_graph_affinities:
        logger.info(
            "Graph/affinities will be skipped if reached (--skip-graph-affinities).",
        )
    elif config.recluster_communities:
        logger.info(
            "Rebuilding artist graph with Louvain recluster (res 10) …",
        )
    else:
        logger.info(
            "Rebuilding artist graph with incremental communities (res 10) …",
        )

    exit_code = run_pipeline_update(config, scrape_mode="cli")

    if exit_code == 0:
        if config.skip_graph_affinities:
            logger.info(
                "Database update complete (reviews + metadata + imputation; "
                "graph skipped).",
            )
        else:
            logger.info(
                "Database update complete (reviews + metadata + imputation + "
                "graph + album_community_affinities).",
            )
        logger.info("Full update pipeline finished.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
