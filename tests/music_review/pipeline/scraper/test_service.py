"""Tests for scraper service module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from music_review.domain.models import Review
from music_review.pipeline.scraper.service import (
    ScrapeResult,
    _finalize_corpus,
    _load_corpus_if_update,
    _process_single,
    scrape_until_gap,
)


def _make_review(review_id: int) -> Review:
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=f"Artist {review_id}",
        album=f"Album {review_id}",
        text=f"Review text for {review_id}",
    )


class TestScrapeResult:
    def test_initial_state(self) -> None:
        r = ScrapeResult()
        assert r.processed == 0
        assert r.scraped_ids == []


class TestLoadCorpusIfUpdate:
    def test_returns_none_when_not_update(self, tmp_path: Path) -> None:
        assert _load_corpus_if_update(tmp_path / "x.jsonl", update_mode=False) is None

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        assert _load_corpus_if_update(tmp_path / "x.jsonl", update_mode=True) is None

    def test_loads_corpus_when_update_and_file_exists(self, tmp_path: Path) -> None:
        path = tmp_path / "reviews.jsonl"
        row = {
            "id": 1,
            "url": "u",
            "artist": "a",
            "album": "b",
            "text": "t",
            "labels": [],
            "tracklist": [],
            "highlights": [],
            "references": [],
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = _load_corpus_if_update(path, update_mode=True)
        assert result is not None
        assert 1 in result


class TestProcessSingle:
    def test_appends_on_non_update(self, tmp_path: Path) -> None:
        path = tmp_path / "reviews.jsonl"
        result = ScrapeResult()

        html = "<html></html>"
        review = _make_review(42)

        with (
            patch(
                "music_review.pipeline.scraper.service.parse_review",
                return_value=review,
            ),
            patch(
                "music_review.pipeline.scraper.service.append_review",
            ) as mock_append,
        ):
            _process_single(
                42,
                html,
                path,
                corpus=None,
                update_mode=False,
                result=result,
            )

        mock_append.assert_called_once_with(path, review)
        assert result.processed == 1
        assert result.scraped_ids == [42]

    def test_updates_corpus_on_update_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "reviews.jsonl"
        corpus: dict[int, dict[str, Any]] = {}
        result = ScrapeResult()
        review = _make_review(7)

        with patch(
            "music_review.pipeline.scraper.service.parse_review",
            return_value=review,
        ):
            _process_single(7, "<html/>", path, corpus, update_mode=True, result=result)

        assert 7 in corpus
        assert corpus[7]["artist"] == "Artist 7"
        assert result.processed == 1

    def test_skips_if_parse_returns_none(self, tmp_path: Path) -> None:
        result = ScrapeResult()
        with patch(
            "music_review.pipeline.scraper.service.parse_review",
            return_value=None,
        ):
            _process_single(1, "<html/>", tmp_path / "x.jsonl", None, False, result)
        assert result.processed == 0


class TestFinalizeCorpus:
    def test_writes_ordered_corpus_in_update_mode(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        corpus = {
            3: {"id": 3, "artist": "C"},
            1: {"id": 1, "artist": "A"},
        }
        result = ScrapeResult()
        result.scraped_ids = [1, 3]

        with patch(
            "music_review.pipeline.scraper.service.write_corpus",
        ) as mock_write:
            _finalize_corpus(corpus, update_mode=True, output_path=path, result=result)

        mock_write.assert_called_once()
        written_reviews = mock_write.call_args[0][1]
        assert [r["id"] for r in written_reviews] == [1, 3]

    def test_noop_in_append_mode(self, tmp_path: Path) -> None:
        result = ScrapeResult()
        with patch(
            "music_review.pipeline.scraper.service.write_corpus",
        ) as mock_write:
            _finalize_corpus(
                None,
                update_mode=False,
                output_path=tmp_path / "x",
                result=result,
            )
        mock_write.assert_not_called()


class TestScrapeUntilGap:
    def test_invalid_stop_after_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="stop_after_n_empty"):
            scrape_until_gap(
                1,
                output_path=tmp_path / "x.jsonl",
                max_rps=100.0,
                stop_after_n_empty=0,
            )
