"""CLI for data-quality checks and health report generation."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from music_review.config import resolve_data_path
from music_review.pipeline.data_quality.models import DataQualityConfig
from music_review.pipeline.data_quality.run import run_data_quality

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run data-quality checks on reviews and imputed metadata; "
            "write pipeline_health_report.json."
        ),
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=Path("data/reviews.jsonl"),
        help="Path to reviews JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--metadata-imputed",
        type=Path,
        default=Path("data/metadata_imputed.jsonl"),
        help="Path to imputed metadata JSONL (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/pipeline_health_report.json"),
        help="Output JSON report path (default: %(default)s).",
    )
    parser.add_argument(
        "--expect-graph-artifacts",
        action="store_true",
        help=(
            "Require non-empty community_memberships.jsonl and "
            "album_community_affinities.jsonl under data/."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any warning is present (not only errors).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="DEBUG logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m music_review.pipeline.data_quality.cli``."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cfg = DataQualityConfig(
        reviews_path=resolve_data_path(args.reviews),
        metadata_imputed_path=resolve_data_path(args.metadata_imputed),
        output_report_path=resolve_data_path(args.output),
        expect_graph_artifacts=args.expect_graph_artifacts,
        strict=args.strict,
    )
    result = run_data_quality(cfg)
    logger.info("Wrote report to %s", result.report_path)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
