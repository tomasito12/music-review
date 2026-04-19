"""Tests for enrichment.fetch_metadata helper behavior."""

from __future__ import annotations

from pathlib import Path

from music_review.pipeline.enrichment import fetch_metadata
from music_review.pipeline.enrichment.musicbrainz_client import (
    ArtistInfo,
    ExternalGenreInfo,
)


def test_split_raw_tag_normalizes_separators() -> None:
    """Separators collapse into a single normalized token."""
    assert fetch_metadata.split_raw_tag("Rock / Indie; Alternative + Pop") == [
        "rock indie alternative pop"
    ]


def test_is_obvious_non_style_detects_non_genre_tokens() -> None:
    """Known non-style tokens are filtered."""
    assert fetch_metadata.is_obvious_non_style("2005")
    assert fetch_metadata.is_obvious_non_style("english")
    assert not fetch_metadata.is_obvious_non_style("shoegaze")


def test_match_genres_from_raw_tag_maps_expected_genres() -> None:
    """Regex mapping finds canonical genres from raw tags."""
    genres = fetch_metadata.match_genres_from_raw_tag("post-punk revival")
    assert "punk" in genres


def test_iter_reviews_skips_invalid_rows(tmp_path: Path) -> None:
    """iter_reviews yields only valid (id, artist, album) tuples."""
    path = tmp_path / "reviews.jsonl"
    path.write_text(
        '{"id": 1, "artist": "A", "album": "B"}\n'
        '{"id": "x", "artist": "C", "album": "D"}\n'
        '{"id": 2, "artist": "E"}\n',
        encoding="utf-8",
    )
    assert list(fetch_metadata.iter_reviews(path)) == [(1, "A", "B")]


def test_fetch_metadata_for_review_with_no_album_info(monkeypatch) -> None:
    """Missing album info yields empty tags/genres and no artist metadata."""
    monkeypatch.setattr(fetch_metadata, "fetch_album_tags", lambda **_: None)
    result = fetch_metadata.fetch_metadata_for_review(10, "A", "B")
    assert result.review_id == 10
    assert result.raw_tags == []
    assert result.genres == []
    assert result.artist_mbid is None


def test_fetch_metadata_for_review_with_artist_info(monkeypatch) -> None:
    """Album and artist information are transferred into metadata."""
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_album_tags",
        lambda **_: ExternalGenreInfo(
            mbid="rg1",
            title="Album",
            artist="Artist",
            tags=["post-punk"],
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info",
        lambda _name: ArtistInfo(
            mbid="a1",
            name="Artist",
            country="DE",
            artist_type="Group",
            disambiguation="",
            tags=["indie"],
            members=["X"],
        ),
    )
    result = fetch_metadata.fetch_metadata_for_review(1, "Artist", "Album")
    assert result.mbid == "rg1"
    assert "punk" in result.genres
    assert result.artist_mbid == "a1"
    assert result.artist_members == ["X"]
