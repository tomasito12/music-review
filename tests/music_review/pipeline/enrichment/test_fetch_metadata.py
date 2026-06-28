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
            artist="Josh.",
            tags=["post-punk"],
            artist_mbid="mbid-from-release-group",
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info_by_mbid",
        lambda _mbid: ArtistInfo(
            mbid="mbid-from-release-group",
            name="Josh.",
            country="DE",
            artist_type="Person",
            disambiguation="Johannes Sumpich",
            tags=["indie"],
            members=[],
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("name lookup should not run"),
        ),
    )
    result = fetch_metadata.fetch_metadata_for_review(1, "Josh.", "Album")
    assert result.mbid == "rg1"
    assert "punk" in result.genres
    assert result.artist_mbid == "mbid-from-release-group"
    assert result.artist_disambiguation == "Johannes Sumpich"


def test_fetch_metadata_for_review_rejects_mismatched_release_group_mbid(
    monkeypatch,
) -> None:
    """A release-group artist MBID is dropped when MusicBrainz name does not match."""
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_album_tags",
        lambda **_: ExternalGenreInfo(
            mbid="rg1",
            title="Album",
            artist="Sue",
            tags=["pop"],
            artist_mbid="f597eafc-4dc5-4bc4-a019-a5035a3c8502",
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info_by_mbid",
        lambda _mbid: ArtistInfo(
            mbid="f597eafc-4dc5-4bc4-a019-a5035a3c8502",
            name="Nancy Wilson",
            country="US",
            artist_type="Person",
            disambiguation=None,
            tags=[],
            members=[],
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info",
        lambda _name: (_ for _ in ()).throw(
            AssertionError("name lookup should not run when MBID was provided"),
        ),
    )
    result = fetch_metadata.fetch_metadata_for_review(1, "Sue", "Album")
    assert result.artist_mbid is None
    assert result.artist_country is None


def test_fetch_metadata_for_review_falls_back_to_name_lookup(monkeypatch) -> None:
    """When release-group credit does not yield an MBID, name lookup is used."""
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_album_tags",
        lambda **_: ExternalGenreInfo(
            mbid="rg1",
            title="Album",
            artist="Sue",
            tags=["pop"],
            artist_mbid=None,
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info_by_mbid",
        lambda _mbid: (_ for _ in ()).throw(
            AssertionError("mbid lookup should not run without release-group MBID"),
        ),
    )
    monkeypatch.setattr(
        fetch_metadata,
        "fetch_artist_info",
        lambda _name: ArtistInfo(
            mbid="sue-mbid",
            name="Sue",
            country="US",
            artist_type="Group",
            disambiguation=None,
            tags=["indie"],
            members=[],
        ),
    )
    result = fetch_metadata.fetch_metadata_for_review(1, "Sue", "Album")
    assert result.artist_mbid == "sue-mbid"
