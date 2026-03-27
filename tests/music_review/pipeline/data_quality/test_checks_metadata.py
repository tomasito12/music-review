"""Tests for imputed metadata JSONL rules."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.data_quality.checks_metadata import scan_metadata_imputed


def test_duplicate_review_id_in_metadata_is_error(tmp_path: Path) -> None:
    meta = tmp_path / "meta.jsonl"
    row = {"review_id": 1, "genres": []}
    meta.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    findings = scan_metadata_imputed(meta, {1}, missing_metadata_warn_rate=0.5)
    assert any(f.code == "METADATA_DUPLICATE_REVIEW_ID" for f in findings)


def test_low_metadata_coverage_warns(tmp_path: Path) -> None:
    meta = tmp_path / "meta.jsonl"
    meta.write_text(
        json.dumps({"review_id": 1, "x": 1}) + "\n",
        encoding="utf-8",
    )
    review_ids = {1, 2, 3, 4}
    findings = scan_metadata_imputed(meta, review_ids, missing_metadata_warn_rate=0.5)
    assert any(f.code == "METADATA_COVERAGE_LOW" for f in findings)
