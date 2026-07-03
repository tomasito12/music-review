"""Tests for the Streamlit-independent playlist service."""

from __future__ import annotations

import random

from music_review.application.playlist_service import PlaylistRequest, PlaylistService
from music_review.domain.models import Review, Track


def _review(review_id: int, *, artist: str, track_title: str) -> Review:
    """Build a review with one highlighted track."""
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=artist,
        album=f"Album {review_id}",
        text=f"{artist} review text",
        rating=8,
        tracklist=[
            Track(number=1, title=track_title, is_highlight=True),
            Track(number=2, title=f"{track_title} Outro"),
        ],
    )


def _request() -> PlaylistRequest:
    """Return a small deterministic playlist request."""
    return PlaylistRequest(
        source="archive",
        playlist_name="Plattenradar Test",
        target_count=2,
        taste_exponent=1.0,
        selection_strategy="stratified",
    )


def test_playlist_service_generates_suggestions_and_exports() -> None:
    """The service returns suggestions plus TXT and CSV export payloads."""
    reviews = [
        _review(1, artist="Artist A", track_title="Song A"),
        _review(2, artist="Artist B", track_title="Song B"),
    ]
    ranked_rows = [
        {"review": reviews[0], "overall_score": 0.7},
        {"review": reviews[1], "overall_score": 0.3},
    ]

    result = PlaylistService().generate(
        reviews=reviews,
        ranked_rows=ranked_rows,
        request=_request(),
        rng=random.Random(7),
    )

    assert len(result.suggestions) == 2
    assert result.txt_export.source == "archive"
    assert result.txt_export.filename == "Plattenradar-Test.txt"
    assert "Artist A - Song A" in result.txt_export.content
    assert result.csv_export.filename == "Plattenradar-Test.csv"
    assert "Track name,Artist name,Playlist name" in result.csv_export.content
    assert len(result.txt_export.items) == 2


def test_playlist_service_export_items_include_artist_mbid() -> None:
    """Export items include artist MBIDs when a review lookup callback is provided."""
    reviews = [
        _review(1, artist="Artist A", track_title="Song A"),
        _review(2, artist="Artist B", track_title="Song B"),
    ]
    ranked_rows = [
        {"review": reviews[0], "overall_score": 0.7},
        {"review": reviews[1], "overall_score": 0.3},
    ]
    mbids = {1: "mbid-a", 2: None}

    result = PlaylistService().generate(
        reviews=reviews,
        ranked_rows=ranked_rows,
        request=_request(),
        rng=random.Random(7),
        artist_mbid_for_review=mbids.get,
    )

    assert result.txt_export.items[0].artist_mbid == "mbid-a"
    assert result.txt_export.items[1].artist_mbid is None


def test_playlist_service_falls_back_to_uniform_album_weights() -> None:
    """Without ranked rows the service can still build a neutral playlist."""
    reviews = [_review(1, artist="Artist A", track_title="Song A")]

    result = PlaylistService().generate(
        reviews=reviews,
        ranked_rows=None,
        request=_request(),
        rng=random.Random(1),
    )

    assert [item.artist for item in result.suggestions] == ["Artist A", "Artist A"]
    assert result.txt_export.items[0].score_weight == 1.0


def test_playlist_service_export_empty_playlist_is_still_downloadable() -> None:
    """Empty suggestions still produce a valid empty export response."""
    export = PlaylistService().build_export(
        suggestions=(),
        source="new_reviews",
        playlist_name="",
        export_format="txt",
    )

    assert export.source == "new_reviews"
    assert export.name == "Plattenradar"
    assert export.filename == "plattenradar.txt"
    assert export.content == ""
    assert export.items == ()
