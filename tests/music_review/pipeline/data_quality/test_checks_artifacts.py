"""Tests for graph artifact presence checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.pipeline.data_quality.checks_artifacts import check_graph_artifacts


def test_graph_artifacts_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "music_review.pipeline.data_quality.checks_artifacts.resolve_data_path",
        lambda _p: tmp_path,
    )
    findings = check_graph_artifacts()
    assert len(findings) >= 2
    assert all(f.severity == "error" for f in findings)


def test_graph_artifacts_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "music_review.pipeline.data_quality.checks_artifacts.resolve_data_path",
        lambda _p: tmp_path,
    )
    (tmp_path / "community_memberships.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    (tmp_path / "album_community_affinities.jsonl").write_text(
        '{"b":2}\n',
        encoding="utf-8",
    )
    findings = check_graph_artifacts()
    assert findings == []
