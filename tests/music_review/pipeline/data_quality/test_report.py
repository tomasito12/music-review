"""Tests for ``music_review.pipeline.data_quality.report``."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.data_quality.models import DataQualityConfig, Finding
from music_review.pipeline.data_quality.report import (
    config_summary_dict,
    findings_to_serialisable,
    write_report,
)


def test_findings_to_serialisable_includes_optional_fields() -> None:
    findings = [
        Finding(
            code="X",
            severity="warning",
            message="m",
            path="/p",
            details={"n": 1},
        ),
    ]
    rows = findings_to_serialisable(findings)
    assert rows[0]["path"] == "/p"
    assert rows[0]["details"] == {"n": 1}


def test_write_report_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    write_report(
        out,
        findings=[
            Finding(code="E", severity="error", message="bad"),
        ],
        config_summary={"k": "v"},
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["error_count"] == 1
    assert data["summary"]["warning_count"] == 0
    assert data["findings"][0]["code"] == "E"


def test_config_summary_dict_keys() -> None:
    cfg = DataQualityConfig(
        reviews_path=Path("/a/reviews.jsonl"),
        metadata_imputed_path=Path("/a/meta.jsonl"),
        output_report_path=Path("/a/out.json"),
        expect_graph_artifacts=True,
        strict=False,
    )
    d = config_summary_dict(cfg)
    assert d["reviews_path"] == "/a/reviews.jsonl"
    assert d["expect_graph_artifacts"] is True
