"""Tests for ``music_review.pipeline.data_quality.cli``."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.data_quality.cli import main as dq_main


def _valid_review(rid: int) -> dict[str, object]:
    return {
        "id": rid,
        "url": f"https://ex/{rid}",
        "artist": "Art",
        "album": "Alb",
        "text": "Enough text in the review body for quality checks here.",
    }


def test_cli_strict_fails_on_warnings(tmp_path: Path) -> None:
    rev = tmp_path / "reviews.jsonl"
    meta = tmp_path / "nope.jsonl"
    report = tmp_path / "out.json"
    rev.write_text(json.dumps(_valid_review(1)) + "\n", encoding="utf-8")
    rc = dq_main(
        [
            "--reviews",
            str(rev),
            "--metadata-imputed",
            str(meta),
            "--output",
            str(report),
            "--strict",
        ],
    )
    assert rc == 1
