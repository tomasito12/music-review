"""Tests for reference-based genre imputation."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.enrichment.reference_imputation import (
    impute_from_references,
    load_artist_profiles,
    load_references_by_review_id,
)


def test_load_references_by_review_id(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.jsonl"
    reviews.write_text(
        json.dumps(
            {
                "id": 1,
                "url": "u",
                "artist": "A",
                "album": "B",
                "text": "t",
                "references": ["Ref One", "Ref Two"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    refs = load_references_by_review_id(reviews)
    assert refs == {1: ["Ref One", "Ref Two"]}


def test_load_artist_profiles_prefers_mbid_key(tmp_path: Path) -> None:
    path = tmp_path / "artist_genres.json"
    path.write_text(
        json.dumps(
            {
                "name:ref one": {"artist_name": "Ref One", "main_genres": ["rock"]},
                "mbid:xyz": {"artist_name": "Ref One", "main_genres": ["indie"]},
            }
        ),
        encoding="utf-8",
    )
    profiles, name_to_key = load_artist_profiles(path)
    assert profiles["mbid:xyz"]["main_genres"] == ["indie"]
    assert name_to_key["ref one"] == "mbid:xyz"


def test_impute_from_references_assigns_genres(tmp_path: Path) -> None:
    imputed = tmp_path / "metadata_imputed.jsonl"
    imputed.write_text(
        json.dumps({"review_id": 1, "artist": "A", "genres": []}) + "\n",
        encoding="utf-8",
    )
    reviews = tmp_path / "reviews.jsonl"
    reviews.write_text(
        json.dumps(
            {
                "id": 1,
                "url": "u",
                "artist": "A",
                "album": "B",
                "text": "t",
                "references": ["Ref Artist"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    artist_genres = tmp_path / "artist_genres.json"
    artist_genres.write_text(
        json.dumps(
            {
                "name:ref artist": {
                    "artist_name": "Ref Artist",
                    "genre_counts": {"shoegaze": 3, "dream pop": 1},
                    "main_genres": ["shoegaze"],
                }
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "out.jsonl"
    count = impute_from_references(
        imputed,
        reviews,
        artist_genres,
        output,
        max_references=1,
    )
    assert count == 1
    row = json.loads(output.read_text(encoding="utf-8").strip())
    assert row["genres"] == ["shoegaze", "dream pop"]
    assert row["genres_inferred_from_references"] is True
    assert row["reference_artists_used"] == ["Ref Artist"]
