"""Tests for ``music_review.pipeline.data_quality.run``."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.data_quality.models import DataQualityConfig
from music_review.pipeline.data_quality.run import run_data_quality


def _valid_review(rid: int) -> dict[str, object]:
    return {
        "id": rid,
        "url": f"https://ex/{rid}",
        "artist": "Art",
        "album": "Alb",
        "text": "Enough text in the review body for quality checks here.",
    }


def test_run_data_quality_writes_report(tmp_path: Path) -> None:
    rev = tmp_path / "reviews.jsonl"
    meta = tmp_path / "meta.jsonl"
    report = tmp_path / "report.json"
    rev.write_text(json.dumps(_valid_review(1)) + "\n", encoding="utf-8")
    meta.write_text(
        json.dumps({"review_id": 1, "genres": ["rock"]}) + "\n",
        encoding="utf-8",
    )
    cfg = DataQualityConfig(
        reviews_path=rev,
        metadata_imputed_path=meta,
        output_report_path=report,
        expect_graph_artifacts=False,
        strict=False,
    )
    result = run_data_quality(cfg)
    assert result.exit_code == 0
    assert report.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert "findings" in data
    assert data["summary"]["error_count"] == 0


def test_run_data_quality_exit_one_on_duplicate_review(tmp_path: Path) -> None:
    rev = tmp_path / "reviews.jsonl"
    meta = tmp_path / "meta.jsonl"
    report = tmp_path / "report.json"
    rev.write_text(
        json.dumps(_valid_review(1)) + "\n" + json.dumps(_valid_review(1)) + "\n",
        encoding="utf-8",
    )
    meta.write_text(json.dumps({"review_id": 1}) + "\n", encoding="utf-8")
    cfg = DataQualityConfig(
        reviews_path=rev,
        metadata_imputed_path=meta,
        output_report_path=report,
        expect_graph_artifacts=False,
        strict=False,
    )
    result = run_data_quality(cfg)
    assert result.exit_code == 1
    assert result.error_count >= 1
