"""Tests for the hourly production update job."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from music_review.pipeline import orchestration, production_update
from music_review.pipeline.orchestration import PipelineConfig
from music_review.pipeline.scraper.service import ScrapeResult


def _config(tmp_path: Path, *, skip_graph: bool = True) -> PipelineConfig:
    return PipelineConfig(
        reviews_path=tmp_path / "reviews.jsonl",
        metadata_path=tmp_path / "metadata.jsonl",
        artist_genres_path=tmp_path / "artist_genres.json",
        metadata_imputed_path=tmp_path / "metadata_imputed.jsonl",
        dq_output_path=tmp_path / "pipeline_health_report.json",
        lock_path=tmp_path / ".production_update.lock",
        max_rps=999.0,
        stop_after_n_empty=3,
        skip_graph_affinities=skip_graph,
        skip_dq=True,
        dq_strict=False,
        exit_if_no_new_reviews=True,
        verbose=False,
    )


def _write_review(path: Path, review_id: int) -> None:
    row = {
        "id": review_id,
        "url": f"https://example.com/{review_id}",
        "artist": "Artist",
        "album": "Album",
        "text": "Text",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def _scrape_result(ids: list[int]) -> ScrapeResult:
    result = ScrapeResult()
    result.scraped_ids = ids
    result.processed = len(ids)
    return result


def test_starts_at_one_when_no_reviews_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int | None] = {}

    def fake_scrape_in_process(config: orchestration.PipelineConfig) -> ScrapeResult:
        _line_count, max_id = orchestration.review_line_count_and_max_id(
            config.reviews_path,
        )
        captured["start_id"] = 1 if max_id is None else max_id + 1
        return _scrape_result([])

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", lambda *_a, **_k: 1)

    assert production_update.run_update(_config(tmp_path)) == 0
    assert captured["start_id"] == 1


def test_skips_enrichment_when_no_new_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 7)
    enrichment_calls: list[tuple[str, list[str]]] = []

    def fake_scrape_in_process(_config: orchestration.PipelineConfig) -> ScrapeResult:
        return _scrape_result([])

    def fake_run_enrichment(*_args: object, **_kwargs: object) -> int:
        enrichment_calls.append(("called", []))
        return 0

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", fake_run_enrichment)

    assert production_update.run_update(_config(tmp_path)) == 0

    assert enrichment_calls == []


def test_new_reviews_run_enrichment_from_first_new_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 10)
    captured: dict[str, int | None] = {}

    def fake_scrape_in_process(_config: orchestration.PipelineConfig) -> ScrapeResult:
        return _scrape_result([11, 12])

    def fake_run_enrichment(
        _config: orchestration.PipelineConfig,
        *,
        metadata_min_review_id: int | None = None,
    ) -> int:
        captured["min_id"] = metadata_min_review_id
        return 0

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", fake_run_enrichment)

    assert production_update.run_update(_config(tmp_path)) == 0

    assert captured["min_id"] == 11


def test_active_lock_makes_cli_exit_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    assert config.lock_path is not None
    config.lock_path.write_text("pid=123\n", encoding="utf-8")

    monkeypatch.setattr(production_update, "build_config", lambda _args: config)

    assert production_update.main([]) == 0
