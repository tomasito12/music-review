"""Production updater for hourly review imports."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from music_review.config import resolve_data_path
from music_review.io.reviews_jsonl import review_line_count_and_max_id
from music_review.pipeline.scraper.service import scrape_until_gap

logger = logging.getLogger(__name__)


class UpdateAlreadyRunningError(RuntimeError):
    """Raised when another production update owns the lock file."""


@dataclass(frozen=True)
class ProductionUpdateConfig:
    """Runtime settings for the production update job."""

    reviews_path: Path
    metadata_path: Path
    artist_genres_path: Path
    metadata_imputed_path: Path
    dq_output_path: Path
    lock_path: Path
    max_rps: float
    stop_after_n_empty: int
    skip_graph_affinities: bool
    skip_dq: bool
    dq_strict: bool
    verbose: bool


def run_module(module: str, args: list[str]) -> bool:
    """Run a pipeline module and report whether it completed successfully."""
    cmd = [sys.executable, "-m", module, *args]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        logger.error("Command failed with exit code %d", result.returncode)
        return False
    return True


@contextlib.contextmanager
def acquire_lock(lock_path: Path) -> Iterator[None]:
    """Create a lock file for one running update, then remove it on exit."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise UpdateAlreadyRunningError(str(lock_path)) from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()


def run_update(config: ProductionUpdateConfig) -> int:
    """Run the hourly production update and skip costly work if nothing changed."""
    with acquire_lock(config.lock_path):
        _line_count, previous_max_id = review_line_count_and_max_id(config.reviews_path)
        start_id = 1 if previous_max_id is None else previous_max_id + 1
        logger.info(
            "Starting production update from review ID %s (previous max: %s).",
            start_id,
            previous_max_id,
        )

        scraper_result = scrape_until_gap(
            start_id,
            output_path=config.reviews_path,
            max_rps=config.max_rps,
            stop_after_n_empty=config.stop_after_n_empty,
        )
        if not scraper_result.scraped_ids:
            logger.info("No new reviews found. Skipping metadata, graph, and DQ steps.")
            return 0

        logger.info(
            "Found %s new reviews (%s-%s). Continuing with enrichment.",
            len(scraper_result.scraped_ids),
            min(scraper_result.scraped_ids),
            max(scraper_result.scraped_ids),
        )

        return _run_enrichment_steps(config, metadata_min_review_id=start_id)


def _run_enrichment_steps(
    config: ProductionUpdateConfig,
    *,
    metadata_min_review_id: int,
) -> int:
    """Run metadata, imputation, graph, labels, and DQ for newly added reviews."""
    if not run_module(
        "music_review.pipeline.enrichment.fetch_metadata",
        [
            "--input",
            str(config.reviews_path),
            "--output",
            str(config.metadata_path),
            "--min-review-id",
            str(metadata_min_review_id),
        ],
    ):
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
        logger.info("Skipping graph and affinity steps (--skip-graph-affinities).")
    elif not _run_graph_and_label_steps(config):
        return 1

    if not config.skip_dq:
        return _run_data_quality(config)

    logger.info("Production update complete (DQ skipped).")
    return 0


def _run_graph_and_label_steps(config: ProductionUpdateConfig) -> bool:
    """Rebuild graph artifacts and refresh missing community labels."""
    if not run_module(
        "music_review.pipeline.retrieval.reference_graph_cli",
        [
            "--reviews",
            str(config.reviews_path),
            "--export-communities",
            "10",
            "--export-album-affinities",
            "--communities-mode",
            "incremental",
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


def _run_data_quality(config: ProductionUpdateConfig) -> int:
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
        logger.info("Production update complete. DQ report: %s", dq_result.report_path)
    return dq_result.exit_code


def build_config(args: argparse.Namespace) -> ProductionUpdateConfig:
    """Translate CLI arguments into resolved production update paths."""
    return ProductionUpdateConfig(
        reviews_path=resolve_data_path(args.reviews),
        metadata_path=resolve_data_path(args.metadata),
        artist_genres_path=resolve_data_path(args.artist_genres),
        metadata_imputed_path=resolve_data_path(args.metadata_imputed),
        dq_output_path=resolve_data_path(args.dq_output),
        lock_path=resolve_data_path(args.lock_file),
        max_rps=args.max_rps,
        stop_after_n_empty=args.stop_after_n_empty,
        skip_graph_affinities=args.skip_graph_affinities,
        skip_dq=args.skip_dq,
        dq_strict=args.dq_strict,
        verbose=args.verbose,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hourly production update for reviews and derived data.",
    )
    parser.add_argument("--reviews", default="data/reviews.jsonl")
    parser.add_argument("--metadata", default="data/metadata.jsonl")
    parser.add_argument("--artist-genres", default="data/artist_genres.json")
    parser.add_argument("--metadata-imputed", default="data/metadata_imputed.jsonl")
    parser.add_argument("--dq-output", default="data/pipeline_health_report.json")
    parser.add_argument("--lock-file", default="data/.production_update.lock")
    parser.add_argument("--max-rps", type=float, default=2.5)
    parser.add_argument("--stop-after-n-empty", type=int, default=3)
    parser.add_argument("--skip-graph-affinities", action="store_true")
    parser.add_argument("--skip-dq", action="store_true")
    parser.add_argument("--dq-strict", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def _configure_logging(*, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for production updates."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=args.verbose)
    config = build_config(args)
    try:
        return run_update(config)
    except UpdateAlreadyRunningError:
        logger.warning(
            "Another production update is already running; lock exists at %s.",
            config.lock_path,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
