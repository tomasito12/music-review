"""Tests for the community_broad_categories pipeline module."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.retrieval.community_broad_categories import (
    build_assign_prompt,
    build_define_categories_prompt,
    load_existing_broad_categories,
    parse_assignment_response,
    parse_categories_response,
)


class TestBuildDefineCategoriesPrompt:
    def test_contains_all_labels_sorted(self) -> None:
        labels = ["Shoegaze", "Ambient", "Post-Punk"]
        prompt = build_define_categories_prompt(labels)
        assert "- Ambient" in prompt
        assert "- Post-Punk" in prompt
        assert "- Shoegaze" in prompt
        assert prompt.index("Ambient") < prompt.index("Post-Punk")

    def test_deduplicates_labels(self) -> None:
        labels = ["Indie", "Indie", "Pop"]
        prompt = build_define_categories_prompt(labels)
        assert prompt.count("- Indie") == 1

    def test_empty_labels(self) -> None:
        prompt = build_define_categories_prompt([])
        assert "JSON-Array" in prompt


class TestBuildAssignPrompt:
    def test_includes_genre_label_and_artists(self) -> None:
        prompt = build_assign_prompt(
            ["Rock", "Pop"],
            "Shoegaze & Dream Pop",
            ["My Bloody Valentine", "Slowdive"],
        )
        assert "Shoegaze & Dream Pop" in prompt
        assert "My Bloody Valentine" in prompt
        assert "Rock" in prompt

    def test_limits_to_five_artists(self) -> None:
        artists = [f"Artist_{i}" for i in range(10)]
        prompt = build_assign_prompt(["Rock"], "Test", artists)
        assert "Artist_4" in prompt
        assert "Artist_5" not in prompt

    def test_no_artists_shows_placeholder(self) -> None:
        prompt = build_assign_prompt(["Rock"], "Test", [])
        assert "(keine Künstler)" in prompt


class TestParseCategoriesResponse:
    def test_valid_json_array(self) -> None:
        text = '["Rock & Alternative", "Electronic & Dance"]'
        assert parse_categories_response(text) == [
            "Rock & Alternative",
            "Electronic & Dance",
        ]

    def test_json_with_surrounding_text(self) -> None:
        text = 'Here are the categories:\n["Rock", "Pop"]\nDone.'
        assert parse_categories_response(text) == ["Rock", "Pop"]

    def test_empty_response(self) -> None:
        assert parse_categories_response("") == []

    def test_invalid_json(self) -> None:
        assert parse_categories_response("not json at all") == []

    def test_non_array_json(self) -> None:
        assert parse_categories_response('{"key": "value"}') == []

    def test_strips_whitespace(self) -> None:
        text = '["  Rock  ", " Pop "]'
        assert parse_categories_response(text) == ["Rock", "Pop"]

    def test_filters_non_strings(self) -> None:
        text = '["Rock", 42, null, "Pop"]'
        assert parse_categories_response(text) == ["Rock", "Pop"]


class TestParseAssignmentResponse:
    def test_valid_assignment(self) -> None:
        valid = ["Rock & Alternative", "Electronic & Dance", "Pop"]
        text = '["Rock & Alternative", "Pop"]'
        result = parse_assignment_response(text, valid)
        assert result == ["Rock & Alternative", "Pop"]

    def test_filters_invalid_categories(self) -> None:
        valid = ["Rock", "Pop"]
        text = '["Rock", "NonExistent", "Pop"]'
        result = parse_assignment_response(text, valid)
        assert result == ["Rock", "Pop"]

    def test_case_insensitive_matching(self) -> None:
        valid = ["Rock & Alternative"]
        text = '["rock & alternative"]'
        result = parse_assignment_response(text, valid)
        assert result == ["Rock & Alternative"]

    def test_empty_response(self) -> None:
        result = parse_assignment_response("", ["Rock"])
        assert result == []


class TestLoadExistingBroadCategories:
    def test_nonexistent_file(self, tmp_path: Path) -> None:
        cats, maps = load_existing_broad_categories(tmp_path / "nope.json")
        assert cats == []
        assert maps == {}

    def test_valid_file(self, tmp_path: Path) -> None:
        data = {
            "resolution": 10,
            "broad_categories": ["Rock", "Pop"],
            "mappings": [
                {
                    "community_id": "C001",
                    "genre_label": "Indie",
                    "broad_categories": ["Rock"],
                },
            ],
        }
        path = tmp_path / "broad.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        cats, maps = load_existing_broad_categories(path)
        assert cats == ["Rock", "Pop"]
        assert maps == {"C001": ["Rock"]}

    def test_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{invalid", encoding="utf-8")
        cats, maps = load_existing_broad_categories(path)
        assert cats == []
        assert maps == {}

    def test_missing_mappings_key(self, tmp_path: Path) -> None:
        data = {"resolution": 10, "broad_categories": ["Rock"]}
        path = tmp_path / "partial.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        cats, maps = load_existing_broad_categories(path)
        assert cats == ["Rock"]
        assert maps == {}
