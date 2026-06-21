"""Production updater for hourly review imports."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from music_review.data_access.paths import (
    DATA_ARTIST_GENRES,
    DATA_METADATA,
    DATA_METADATA_IMPUTED,
    DATA_PIPELINE_HEALTH_REPORT,
    DATA_PRODUCTION_UPDATE_LOCK,
    DATA_REVIEWS,
)
from music_review.pipeline.orchestration import (
    PipelineConfig,
    production_config_from_namespace,
    run_pipeline_update,
)

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


def _to_pipeline_config(config: ProductionUpdateConfig) -> PipelineConfig:
    return PipelineConfig(
        reviews_path=config.reviews_path,
        metadata_path=config.metadata_path,
        artist_genres_path=config.artist_genres_path,
        metadata_imputed_path=config.metadata_imputed_path,
        dq_output_path=config.dq_output_path,
        lock_path=config.lock_path,
        max_rps=config.max_rps,
        stop_after_n_empty=config.stop_after_n_empty,
        skip_graph_affinities=config.skip_graph_affinities,
        skip_dq=config.skip_dq,
        dq_strict=config.dq_strict,
        exit_if_no_new_reviews=True,
        verbose=config.verbose,
    )


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
        return run_pipeline_update(
            _to_pipeline_config(config),
            scrape_mode="in_process",
        )


def build_config(args: argparse.Namespace) -> ProductionUpdateConfig:
    """Translate CLI arguments into resolved production update paths."""
    pipeline_cfg = production_config_from_namespace(args)
    return ProductionUpdateConfig(
        reviews_path=pipeline_cfg.reviews_path,
        metadata_path=pipeline_cfg.metadata_path,
        artist_genres_path=pipeline_cfg.artist_genres_path,
        metadata_imputed_path=pipeline_cfg.metadata_imputed_path,
        dq_output_path=pipeline_cfg.dq_output_path,
        lock_path=pipeline_cfg.lock_path or Path(DATA_PRODUCTION_UPDATE_LOCK),
        max_rps=pipeline_cfg.max_rps,
        stop_after_n_empty=pipeline_cfg.stop_after_n_empty,
        skip_graph_affinities=pipeline_cfg.skip_graph_affinities,
        skip_dq=pipeline_cfg.skip_dq,
        dq_strict=pipeline_cfg.dq_strict,
        verbose=pipeline_cfg.verbose,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hourly production update for reviews and derived data.",
    )
    parser.add_argument("--reviews", default=DATA_REVIEWS)
    parser.add_argument("--metadata", default=DATA_METADATA)
    parser.add_argument("--artist-genres", default=DATA_ARTIST_GENRES)
    parser.add_argument("--metadata-imputed", default=DATA_METADATA_IMPUTED)
    parser.add_argument("--dq-output", default=DATA_PIPELINE_HEALTH_REPORT)
    parser.add_argument("--lock-file", default=DATA_PRODUCTION_UPDATE_LOCK)
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
