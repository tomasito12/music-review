"""Shared pipeline orchestration for manual and production updates."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

from music_review.config import resolve_data_path
from music_review.data_access.paths import (
    DATA_ARTIST_GENRES,
    DATA_METADATA,
    DATA_METADATA_IMPUTED,
    DATA_PIPELINE_HEALTH_REPORT,
    DATA_PRODUCTION_UPDATE_LOCK,
    DATA_REVIEWS,
)
from music_review.io.reviews_jsonl import review_line_count_and_max_id
from music_review.pipeline.scraper.service import ScrapeResult, scrape_until_gap

logger = logging.getLogger(__name__)


class CommunitiesMode(StrEnum):
    """How community IDs are assigned during graph export."""

    INCREMENTAL = "incremental"
    LOUVAIN = "louvain"


@dataclass(frozen=True)
class PipelineConfig:
    """Runtime settings for a full or incremental database update."""

    reviews_path: Path
    metadata_path: Path
    artist_genres_path: Path
    metadata_imputed_path: Path
    dq_output_path: Path
    lock_path: Path | None = None
    max_rps: float = 2.5
    stop_after_n_empty: int = 3
    skip_reviews: bool = False
    skip_graph_affinities: bool = False
    skip_dq: bool = False
    dq_strict: bool = False
    recluster_communities: bool = False
    metadata_update: bool = False
    metadata_min_review_id: int | None = None
    max_id: int | None = None
    exit_if_no_new_reviews: bool = False
    verbose: bool = False


def run_module(module: str, args: list[str]) -> bool:
    """Run a pipeline module subprocess and report success."""
    cmd = [sys.executable, "-m", module, *args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d", result.returncode)
        return False
    return True


def communities_mode_for_config(config: PipelineConfig) -> CommunitiesMode:
    """Map config flags to graph CLI communities mode."""
    if config.recluster_communities:
        return CommunitiesMode.LOUVAIN
    return CommunitiesMode.INCREMENTAL


def run_enrichment_steps(
    config: PipelineConfig,
    *,
    metadata_min_review_id: int | None = None,
) -> int:
    """Run metadata, imputation, graph, labels, and optional DQ."""
    fetch_args = [
        "--input",
        str(config.reviews_path),
        "--output",
        str(config.metadata_path),
    ]
    if config.metadata_update:
        fetch_args.append("--update")
    min_id = (
        metadata_min_review_id
        if metadata_min_review_id is not None
        else (config.metadata_min_review_id)
    )
    if min_id is not None:
        fetch_args.extend(["--min-review-id", str(min_id)])
    if not run_module("music_review.pipeline.enrichment.fetch_metadata", fetch_args):
        return 1

    if not run_module(
        "music_review.pipeline.enrichment.artist_genres",
        [
            "--metadata",
            str(config.metadata_path),
            "--artist-profiles-output",
            str(config.artist_genres_path),
            "--imputed-metadata-output",
            str(config.metadata_imputed_path),
        ],
    ):
        return 1

    if not run_module(
        "music_review.pipeline.enrichment.reference_imputation",
        [
            "--imputed-metadata",
            str(config.metadata_imputed_path),
            "--reviews",
            str(config.reviews_path),
            "--artist-genres",
            str(config.artist_genres_path),
        ],
    ):
        return 1

    if config.skip_graph_affinities:
        logger.info("Skipping graph and affinity steps.")
    elif not run_graph_and_label_steps(config):
        return 1

    if config.skip_dq:
        logger.info("Pipeline enrichment complete (DQ skipped).")
        return 0

    return run_data_quality(config)


def run_graph_and_label_steps(config: PipelineConfig) -> bool:
    """Rebuild graph artifacts and refresh missing community labels."""
    mode = communities_mode_for_config(config)
    if not run_module(
        "music_review.pipeline.retrieval.reference_graph_cli",
        [
            "--reviews",
            str(config.reviews_path),
            "--export-communities",
            "10",
            "--export-album-affinities",
            "--communities-mode",
            mode.value,
        ],
    ):
        return False

    if os.environ.get("OPENAI_API_KEY"):
        logger.info("Labeling missing communities and broad categories.")
        if not run_module(
            "music_review.pipeline.retrieval.community_genre_labels",
            ["--only-missing"],
        ):
            logger.warning("community-genre-labels failed; continuing.")
        if not run_module(
            "music_review.pipeline.retrieval.community_broad_categories",
            ["--only-missing"],
        ):
            logger.warning("community-broad-categories failed; continuing.")
    return True


def run_data_quality(config: PipelineConfig) -> int:
    """Write the data-quality health report and return its exit code."""
    from music_review.pipeline.data_quality.models import DataQualityConfig
    from music_review.pipeline.data_quality.run import run_data_quality

    dq_cfg = DataQualityConfig(
        reviews_path=config.reviews_path,
        metadata_imputed_path=config.metadata_imputed_path,
        output_report_path=config.dq_output_path,
        expect_graph_artifacts=not config.skip_graph_affinities,
        strict=config.dq_strict,
    )
    dq_result = run_data_quality(dq_cfg)
    if dq_result.exit_code != 0:
        logger.error(
            "Data-quality checks failed (exit %s). See %s.",
            dq_result.exit_code,
            dq_result.report_path,
        )
    else:
        logger.info("Pipeline update complete. DQ report: %s", dq_result.report_path)
    return dq_result.exit_code


def scrape_via_cli(config: PipelineConfig) -> bool:
    """Run the scraper CLI in resume mode."""
    scraper_args: list[str] = []
    if config.verbose:
        scraper_args.append("-v")
    scraper_args.extend(["--output", str(config.reviews_path), "resume"])
    if config.max_id is not None:
        scraper_args.extend(["--max-id", str(config.max_id)])
    return run_module("music_review.pipeline.scraper.cli", scraper_args)


def scrape_in_process(config: PipelineConfig) -> ScrapeResult:
    """Scrape new reviews in-process from the next ID after the corpus max."""
    _line_count, previous_max_id = review_line_count_and_max_id(config.reviews_path)
    start_id = 1 if previous_max_id is None else previous_max_id + 1
    logger.info(
        "Starting in-process scrape from review ID %s (previous max: %s).",
        start_id,
        previous_max_id,
    )
    return scrape_until_gap(
        start_id,
        output_path=config.reviews_path,
        max_rps=config.max_rps,
        stop_after_n_empty=config.stop_after_n_empty,
    )


def run_pipeline_update(
    config: PipelineConfig,
    *,
    scrape_mode: str = "cli",
) -> int:
    """Run the full update pipeline with a pluggable scrape strategy.

    ``scrape_mode`` is either ``cli`` (subprocess resume) or ``in_process``
    (direct ``scrape_until_gap`` with optional early exit).
    """
    metadata_min_review_id: int | None = config.metadata_min_review_id

    if not config.skip_reviews:
        if scrape_mode == "in_process":
            scraper_result = scrape_in_process(config)
            if not scraper_result.scraped_ids:
                if config.exit_if_no_new_reviews:
                    logger.info(
                        "No new reviews found. Skipping metadata, graph, and DQ steps.",
                    )
                    return 0
            else:
                logger.info(
                    "Found %s new reviews (%s-%s). Continuing with enrichment.",
                    len(scraper_result.scraped_ids),
                    min(scraper_result.scraped_ids),
                    max(scraper_result.scraped_ids),
                )
                metadata_min_review_id = min(scraper_result.scraped_ids)
        elif not scrape_via_cli(config):
            return 1

    return run_enrichment_steps(
        config,
        metadata_min_review_id=metadata_min_review_id,
    )


def pipeline_config_from_namespace(args: argparse.Namespace) -> PipelineConfig:
    """Build a resolved :class:`PipelineConfig` from CLI arguments."""
    return PipelineConfig(
        reviews_path=resolve_data_path(getattr(args, "reviews", DATA_REVIEWS)),
        metadata_path=resolve_data_path(getattr(args, "metadata", DATA_METADATA)),
        artist_genres_path=resolve_data_path(
            getattr(args, "artist_genres", DATA_ARTIST_GENRES),
        ),
        metadata_imputed_path=resolve_data_path(
            getattr(args, "metadata_imputed", DATA_METADATA_IMPUTED),
        ),
        dq_output_path=resolve_data_path(
            getattr(args, "dq_output", DATA_PIPELINE_HEALTH_REPORT),
        ),
        lock_path=resolve_data_path(
            getattr(args, "lock_file", DATA_PRODUCTION_UPDATE_LOCK),
        ),
        max_rps=float(getattr(args, "max_rps", 2.5)),
        stop_after_n_empty=int(getattr(args, "stop_after_n_empty", 3)),
        skip_reviews=bool(getattr(args, "skip_reviews", False)),
        skip_graph_affinities=bool(getattr(args, "skip_graph_affinities", False)),
        skip_dq=bool(getattr(args, "skip_dq", False)),
        dq_strict=bool(getattr(args, "dq_strict", False)),
        recluster_communities=bool(getattr(args, "recluster_communities", False)),
        metadata_update=bool(getattr(args, "metadata_update", False)),
        metadata_min_review_id=getattr(args, "metadata_min_review_id", None),
        max_id=getattr(args, "max_id", None),
        exit_if_no_new_reviews=bool(getattr(args, "exit_if_no_new_reviews", False)),
        verbose=bool(getattr(args, "verbose", False)),
    )


def production_config_from_namespace(args: argparse.Namespace) -> PipelineConfig:
    """Production updater config: in-process scrape with early exit."""
    return replace(
        pipeline_config_from_namespace(args),
        exit_if_no_new_reviews=True,
    )
