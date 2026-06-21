"""Tests for artist genre profile building and data access."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.data_access.artist_genres import load_artist_genre_profiles
from music_review.pipeline.enrichment.artist_genres import (
    ArtistGenreProfile,
    build_artist_genre_profiles,
    save_artist_genre_profiles,
)


def test_load_artist_genre_profiles_missing_returns_empty(tmp_path: Path) -> None:
    assert load_artist_genre_profiles(tmp_path / "missing.json") == {}


def test_load_artist_genre_profiles_reads_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "artist_genres.json"
    path.write_text(
        json.dumps(
            {
                "mbid:abc": {
                    "artist_name": "Radiohead",
                    "main_genres": ["art rock"],
                },
                "bad": "not-a-dict",
            }
        ),
        encoding="utf-8",
    )
    profiles = load_artist_genre_profiles(path)
    assert profiles == {
        "mbid:abc": {
            "artist_name": "Radiohead",
            "main_genres": ["art rock"],
        },
    }


def test_build_artist_genre_profiles_groups_by_mbid(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.jsonl"
    metadata.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "review_id": 1,
                        "artist": "Radiohead",
                        "artist_mbid": "mbid-1",
                        "genres": ["art rock", "alternative rock"],
                    }
                ),
                json.dumps(
                    {
                        "review_id": 2,
                        "artist": "Radiohead",
                        "artist_mbid": "mbid-1",
                        "genres": ["art rock"],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    profiles = build_artist_genre_profiles(metadata, min_genre_share=0.4)
    assert len(profiles) == 1
    profile = profiles["mbid:mbid-1"]
    assert isinstance(profile, ArtistGenreProfile)
    assert profile.total_albums == 2
    assert "art rock" in profile.main_genres


def test_save_artist_genre_profiles_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "artist_genres.json"
    profiles = {
        "name:test": ArtistGenreProfile(
            artist_mbid=None,
            artist_name="Test",
            total_albums=1,
            genre_counts={"rock": 1},
            main_genres=["rock"],
        )
    }
    save_artist_genre_profiles(profiles, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["name:test"]["main_genres"] == ["rock"]
