"""Tests for the hourly production update job."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from music_review.pipeline import production_update
from music_review.pipeline.production_update import ProductionUpdateConfig
from music_review.pipeline.scraper.service import ScrapeResult


def _config(tmp_path: Path, *, skip_graph: bool = True) -> ProductionUpdateConfig:
    return ProductionUpdateConfig(
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
    calls: list[dict[str, Any]] = []

    def fake_scrape_until_gap(*args: Any, **kwargs: Any) -> ScrapeResult:
        calls.append({"args": args, "kwargs": kwargs})
        return _scrape_result([])

    monkeypatch.setattr(production_update, "scrape_until_gap", fake_scrape_until_gap)
    monkeypatch.setattr(production_update, "run_module", lambda *_args: False)

    assert production_update.run_update(_config(tmp_path)) == 0

    assert calls[0]["args"] == (1,)
    assert calls[0]["kwargs"]["stop_after_n_empty"] == 3


def test_skips_enrichment_when_no_new_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 7)
    module_calls: list[tuple[str, list[str]]] = []

    def fake_scrape_until_gap(*args: Any, **kwargs: Any) -> ScrapeResult:
        assert args == (8,)
        return _scrape_result([])

    def fake_run_module(module: str, args: list[str]) -> bool:
        module_calls.append((module, args))
        return True

    monkeypatch.setattr(production_update, "scrape_until_gap", fake_scrape_until_gap)
    monkeypatch.setattr(production_update, "run_module", fake_run_module)

    assert production_update.run_update(_config(tmp_path)) == 0

    assert module_calls == []


def test_new_reviews_run_enrichment_from_first_new_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 10)
    module_calls: list[tuple[str, list[str]]] = []

    def fake_scrape_until_gap(*args: Any, **kwargs: Any) -> ScrapeResult:
        assert args == (11,)
        return _scrape_result([11, 12])

    def fake_run_module(module: str, args: list[str]) -> bool:
        module_calls.append((module, args))
        return True

    monkeypatch.setattr(production_update, "scrape_until_gap", fake_scrape_until_gap)
    monkeypatch.setattr(production_update, "run_module", fake_run_module)

    assert production_update.run_update(_config(tmp_path)) == 0

    assert module_calls[0][0] == "music_review.pipeline.enrichment.fetch_metadata"
    assert "--min-review-id" in module_calls[0][1]
    assert module_calls[0][1][-1] == "11"
    assert [call[0] for call in module_calls] == [
        "music_review.pipeline.enrichment.fetch_metadata",
        "music_review.pipeline.enrichment.artist_genres",
        "music_review.pipeline.enrichment.reference_imputation",
    ]


def test_active_lock_makes_cli_exit_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    config.lock_path.write_text("pid=123\n", encoding="utf-8")

    monkeypatch.setattr(production_update, "build_config", lambda _args: config)

    assert production_update.main([]) == 0
