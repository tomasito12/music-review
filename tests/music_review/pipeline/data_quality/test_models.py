"""Tests for ``music_review.pipeline.data_quality.models``."""

from __future__ import annotations

from pathlib import Path

from music_review.pipeline.data_quality.models import (
    DataQualityConfig,
    DataQualityResult,
    Finding,
)


def test_data_quality_result_counts() -> None:
    result = DataQualityResult(
        findings=[
            Finding(code="a", severity="error", message="e"),
            Finding(code="b", severity="warning", message="w"),
        ],
        report_path=Path("/tmp/x"),
        exit_code=1,
    )
    assert result.error_count == 1
    assert result.warning_count == 1


def test_data_quality_config_defaults() -> None:
    cfg = DataQualityConfig(
        reviews_path=Path("r.jsonl"),
        metadata_imputed_path=Path("m.jsonl"),
        output_report_path=Path("o.json"),
        expect_graph_artifacts=False,
        strict=False,
    )
    assert cfg.empty_text_warn_rate == 0.01
    assert cfg.short_text_chars == 50
