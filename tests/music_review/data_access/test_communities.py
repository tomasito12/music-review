"""Tests for community artifact loaders."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.data_access.communities import (
    load_artist_communities,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
)


def test_load_artist_communities_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "community_memberships.jsonl"
    row = {
        "artist_id": "artist_a",
        "communities": {"res_10": "C001"},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    loaded = load_artist_communities(path)
    assert loaded["artist_a"]["res_10"] == "C001"


def test_load_communities_res_10_filters_invalid_entries(tmp_path: Path) -> None:
    path = tmp_path / "communities_res_10.json"
    path.write_text(
        json.dumps(
            {
                "communities": [
                    {"id": "C001", "top_artists": ["A"]},
                    {"top_artists": ["B"]},
                    "bad",
                ],
            },
        ),
        encoding="utf-8",
    )
    comms = load_communities_res_10(path)
    assert len(comms) == 1
    assert comms[0]["id"] == "C001"


def test_load_genre_labels_res_10(tmp_path: Path) -> None:
    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps(
            {
                "labels": [
                    {"community_id": "C001", "genre_label": "Rock"},
                    {"community_id": "C002"},
                ],
            },
        ),
        encoding="utf-8",
    )
    labels = load_genre_labels_res_10(path)
    assert labels == {"C001": "Rock"}


def test_load_broad_categories_res_10(tmp_path: Path) -> None:
    path = tmp_path / "broad.json"
    path.write_text(
        json.dumps(
            {
                "broad_categories": ["Pop", "Rock"],
                "mappings": [
                    {"community_id": "C001", "broad_categories": ["Rock"]},
                ],
            },
        ),
        encoding="utf-8",
    )
    cats, mapping = load_broad_categories_res_10(path)
    assert cats == ["Pop", "Rock"]
    assert mapping["C001"] == ["Rock"]
