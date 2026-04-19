"""Orchestrate data-quality checks and exit-code policy."""

from __future__ import annotations

import logging

from music_review.pipeline.data_quality.checks_artifacts import check_graph_artifacts
from music_review.pipeline.data_quality.checks_metadata import scan_metadata_imputed
from music_review.pipeline.data_quality.checks_reviews import scan_reviews_jsonl
from music_review.pipeline.data_quality.models import (
    DataQualityConfig,
    DataQualityResult,
    Finding,
)
from music_review.pipeline.data_quality.report import (
    config_summary_dict,
    write_report,
)

logger = logging.getLogger(__name__)


def run_data_quality(cfg: DataQualityConfig) -> DataQualityResult:
    """Run all configured checks, write report, and compute exit code.

    Exit policy: 1 if any error, or if ``strict`` and any warning; else 0.
    """
    findings: list[Finding] = []

    rev_findings, stats = scan_reviews_jsonl(
        cfg.reviews_path,
        short_text_chars=cfg.short_text_chars,
        year_min=cfg.year_min,
        rating_min=cfg.rating_min,
        rating_max=cfg.rating_max,
        empty_text_warn_rate=cfg.empty_text_warn_rate,
        short_text_warn_rate=cfg.short_text_warn_rate,
    )
    findings.extend(rev_findings)

    meta_findings = scan_metadata_imputed(
        cfg.metadata_imputed_path,
        stats.review_ids,
        missing_metadata_warn_rate=cfg.missing_metadata_warn_rate,
    )
    findings.extend(meta_findings)

    if cfg.expect_graph_artifacts:
        findings.extend(check_graph_artifacts())

    write_report(
        cfg.output_report_path,
        findings=findings,
        config_summary=config_summary_dict(cfg),
    )

    err_n = sum(1 for f in findings if f.severity == "error")
    warn_n = sum(1 for f in findings if f.severity == "warning")
    logger.info("DQ summary: %d error(s), %d warning(s).", err_n, warn_n)

    exit_code = 0
    if err_n > 0 or (cfg.strict and warn_n > 0):
        exit_code = 1

    return DataQualityResult(
        findings=findings,
        report_path=cfg.output_report_path,
        exit_code=exit_code,
    )
