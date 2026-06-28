"""Tests for shared pipeline orchestration."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from music_review.pipeline import orchestration
from music_review.pipeline.orchestration import (
    CommunitiesMode,
    PipelineConfig,
    communities_mode_for_config,
    run_pipeline_update,
)
from music_review.pipeline.scraper.service import ScrapeResult


def _config(tmp_path: Path, **overrides: object) -> PipelineConfig:
    base = PipelineConfig(
        reviews_path=tmp_path / "reviews.jsonl",
        metadata_path=tmp_path / "metadata.jsonl",
        artist_genres_path=tmp_path / "artist_genres.json",
        metadata_imputed_path=tmp_path / "metadata_imputed.jsonl",
        dq_output_path=tmp_path / "pipeline_health_report.json",
        skip_dq=True,
        skip_graph_affinities=True,
    )
    return replace(base, **overrides)


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


def test_communities_mode_for_config() -> None:
    cfg = _config(Path("/tmp"), recluster_communities=True)
    assert communities_mode_for_config(cfg) == CommunitiesMode.LOUVAIN
    cfg_default = _config(Path("/tmp"))
    assert communities_mode_for_config(cfg_default) == CommunitiesMode.INCREMENTAL


def test_cli_scrape_mode_invokes_scraper_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_scrape_cli(config: PipelineConfig) -> bool:
        calls.append(["cli", str(config.reviews_path)])
        return True

    monkeypatch.setattr(orchestration, "scrape_via_cli", fake_scrape_cli)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", lambda *_a, **_k: 0)

    cfg = _config(tmp_path)
    assert run_pipeline_update(cfg, scrape_mode="cli") == 0
    assert calls == [["cli", str(cfg.reviews_path)]]


def test_in_process_early_exit_when_no_new_reviews(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 7)
    enrichment_calls: list[Any] = []

    def fake_scrape_in_process(config: PipelineConfig) -> ScrapeResult:
        assert config.exit_if_no_new_reviews is True
        return _scrape_result([])

    def fake_enrichment(config: PipelineConfig, **kwargs: object) -> int:
        enrichment_calls.append((config, kwargs))
        return 0

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", fake_enrichment)

    cfg = _config(tmp_path, exit_if_no_new_reviews=True)
    assert run_pipeline_update(cfg, scrape_mode="in_process") == 0
    assert enrichment_calls == []


def test_in_process_runs_enrichment_from_first_new_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_review(tmp_path / "reviews.jsonl", 10)
    captured: dict[str, Any] = {}

    def fake_scrape_in_process(_config: PipelineConfig) -> ScrapeResult:
        return _scrape_result([11, 12])

    def fake_enrichment(
        config: PipelineConfig,
        *,
        metadata_min_review_id: int | None = None,
        artist_image_review_ids: frozenset[int] | None = None,
    ) -> int:
        captured["min_id"] = metadata_min_review_id
        return 0

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", fake_enrichment)

    cfg = _config(tmp_path, exit_if_no_new_reviews=True)
    assert run_pipeline_update(cfg, scrape_mode="in_process") == 0
    assert captured["min_id"] == 11


def test_run_enrichment_steps_fetches_artist_images_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Optional artist image fetch runs after enrichment when requested."""
    fetch_calls: list[frozenset[int] | None] = []

    monkeypatch.setattr(orchestration, "run_module", lambda *_a, **_k: True)
    monkeypatch.setattr(
        orchestration,
        "run_artist_image_fetch",
        lambda config, *, artist_image_review_ids=None: (
            fetch_calls.append(artist_image_review_ids) or 0
        ),
    )

    cfg = _config(tmp_path, fetch_artist_images=True, skip_dq=True)
    review_ids = frozenset({11, 12})
    assert (
        orchestration.run_enrichment_steps(
            cfg,
            artist_image_review_ids=review_ids,
        )
        == 0
    )
    assert fetch_calls == [review_ids]


def test_in_process_passes_scraped_review_ids_to_enrichment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production scrape passes the new review id set for artist image prefetch."""
    _write_review(tmp_path / "reviews.jsonl", 10)
    captured: dict[str, Any] = {}

    def fake_scrape_in_process(_config: PipelineConfig) -> ScrapeResult:
        return _scrape_result([11, 12])

    def fake_enrichment(
        _config: PipelineConfig,
        *,
        metadata_min_review_id: int | None = None,
        artist_image_review_ids: frozenset[int] | None = None,
    ) -> int:
        captured["min_id"] = metadata_min_review_id
        captured["review_ids"] = artist_image_review_ids
        return 0

    monkeypatch.setattr(orchestration, "scrape_in_process", fake_scrape_in_process)
    monkeypatch.setattr(orchestration, "run_enrichment_steps", fake_enrichment)

    cfg = _config(tmp_path, exit_if_no_new_reviews=True, fetch_artist_images=True)
    assert run_pipeline_update(cfg, scrape_mode="in_process") == 0
    assert captured["min_id"] == 11
    assert captured["review_ids"] == frozenset({11, 12})


def test_run_artist_image_fetch_scoped_to_review_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artist image fetch for a review batch processes only those artists."""
    metadata_path = tmp_path / "metadata_imputed.jsonl"
    metadata_path.write_text(
        "\n".join(
            [
                '{"review_id": 10, "artist": "Old", "artist_mbid": "mbid-old"}',
                '{"review_id": 11, "artist": "New", "artist_mbid": "mbid-new"}',
            ],
        ),
        encoding="utf-8",
    )
    batch_calls: list[tuple[list[str], bool]] = []

    class FakeService:
        pass

    def fake_run_batch(
        _service: object,
        targets: list[object],
        *,
        limit: int,
        missing_only: bool,
        process_all: bool,
    ) -> object:
        batch_calls.append(
            (
                [
                    getattr(target, "artist_mbid", "")
                    for target in targets  # type: ignore[union-attr]
                ],
                process_all,
            ),
        )
        from music_review.application.artist_image_batch import ArtistImageBatchReport

        return ArtistImageBatchReport()

    monkeypatch.setattr(
        "music_review.application.artist_image_service.batch_artist_image_service",
        lambda: FakeService(),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_batch.run_artist_image_batch",
        fake_run_batch,
    )

    cfg = _config(
        tmp_path,
        metadata_imputed_path=metadata_path,
        fetch_artist_images=True,
    )
    assert (
        orchestration.run_artist_image_fetch(
            cfg,
            artist_image_review_ids=frozenset({11}),
        )
        == 0
    )
    assert batch_calls == [(["mbid-new"], True)]
