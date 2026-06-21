"""Tests for reference_graph_cli module."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.retrieval.reference_graph_cli import (
    _parse_float_list,
    main,
)


class TestParseFloatList:
    def test_valid_floats(self) -> None:
        result = _parse_float_list("1.0,2.5,0.5")
        assert result == [0.5, 1.0, 2.5]

    def test_deduplicates(self) -> None:
        result = _parse_float_list("1.0,1.0,2.0")
        assert result == [1.0, 2.0]

    def test_empty_string(self) -> None:
        result = _parse_float_list("")
        assert result == []

    def test_whitespace_handling(self) -> None:
        result = _parse_float_list(" 3.0 , 1.0 ")
        assert result == [1.0, 3.0]

    def test_invalid_returns_none(self) -> None:
        assert _parse_float_list("abc,def") is None

    def test_mixed_valid_invalid_returns_none(self) -> None:
        assert _parse_float_list("1.0,abc") is None

    def test_single_value(self) -> None:
        assert _parse_float_list("10") == [10.0]


class TestMainReturnsErrorOnMissingFile:
    def test_nonexistent_reviews_file(self, tmp_path: Path) -> None:
        fake_reviews = tmp_path / "nonexistent.jsonl"
        rc = main(["--reviews", str(fake_reviews)])
        assert rc == 1


def _minimal_reviews_jsonl(path: Path) -> None:
    row = {
        "id": 1,
        "url": "https://example.com/1",
        "artist": "Artist A",
        "album": "Album One",
        "text": "Review text",
        "references": ["Ref B"],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


class TestExportCommunitiesErrors:
    def test_invalid_export_communities_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        reviews = tmp_path / "reviews.jsonl"
        output = tmp_path / "graph.graphml"
        _minimal_reviews_jsonl(reviews)
        rc = main(
            [
                "--reviews",
                str(reviews),
                "--output",
                str(output),
                "--export-communities",
                "abc",
            ],
        )
        assert rc == 1

    def test_empty_export_communities_returns_error(
        self,
        tmp_path: Path,
    ) -> None:
        reviews = tmp_path / "reviews.jsonl"
        output = tmp_path / "graph.graphml"
        _minimal_reviews_jsonl(reviews)
        rc = main(
            [
                "--reviews",
                str(reviews),
                "--output",
                str(output),
                "--export-communities",
                "",
            ],
        )
        assert rc == 1
