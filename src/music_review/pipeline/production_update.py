"""Production updater for hourly review imports."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import sys
from collections.abc import Iterator

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


@contextlib.contextmanager
def acquire_lock(lock_path: os.PathLike[str] | str) -> Iterator[None]:
    """Create a lock file for one running update, then remove it on exit."""
    lock = os.fspath(lock_path)
    lock_dir = os.path.dirname(lock)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise UpdateAlreadyRunningError(lock) from exc

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(lock)


def run_update(config: PipelineConfig) -> int:
    """Run the hourly production update and skip costly work if nothing changed."""
    if config.lock_path is None:
        msg = "Production update requires lock_path on PipelineConfig."
        raise ValueError(msg)
    with acquire_lock(config.lock_path):
        return run_pipeline_update(config, scrape_mode="in_process")


def build_config(args: argparse.Namespace) -> PipelineConfig:
    """Translate CLI arguments into a resolved production pipeline config."""
    return production_config_from_namespace(args)


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
