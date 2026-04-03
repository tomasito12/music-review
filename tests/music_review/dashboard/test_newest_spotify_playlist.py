from __future__ import annotations

import logging
import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.newest_spotify_playlist import (
    _artist_matches_review_vs_spotify,
    _strip_trailing_feat_credit_suffixes,
    _titles_match_review_vs_spotify,
    build_album_weights,
    build_playlist_candidates,
    candidate_tracks_for_review,
    pick_track_title_for_iteration,
    resolve_track_uri_strict,
    spotify_resolve_query_variants,
)
from music_review.domain.models import Review, Track
from music_review.integrations.spotify_client import SpotifyToken, SpotifyTrack


def _review(
    review_id: int,
    *,
    artist: str = "Artist",
    album: str = "Album",
    tracks: list[Track] | None = None,
    highlights: list[str] | None = None,
) -> Review:
    return Review(
        id=review_id,
        url=f"https://example.org/{review_id}",
        artist=artist,
        album=album,
        text="text",
        tracklist=tracks or [],
        highlights=highlights or [],
    )


def _token() -> SpotifyToken:
    return SpotifyToken(
        access_token="token",
        token_type="Bearer",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
    )


def test_build_album_weights_uses_normalized_scores() -> None:
    reviews = [_review(1), _review(2)]
    rows = [
        {"review": reviews[0], "overall_score": 2.0},
        {"review": reviews[1], "overall_score": 6.0},
    ]

    picked, weights = build_album_weights(reviews, rows)

    assert picked == reviews
    assert weights == [0.25, 0.75]


def test_build_album_weights_without_ranking_is_uniform() -> None:
    reviews = [_review(1), _review(2), _review(3)]

    picked, weights = build_album_weights(reviews, None)

    assert picked == reviews
    assert weights == [1 / 3, 1 / 3, 1 / 3]


def test_build_album_weights_three_scores_match_relative_probabilities() -> None:
    """Scores 0.3, 0.1, 0.1 normalize to 3/5, 1/5, 1/5 (user-facing example)."""
    r1, r2, r3 = _review(1), _review(2), _review(3)
    rows = [
        {"review": r1, "overall_score": 0.3},
        {"review": r2, "overall_score": 0.1},
        {"review": r3, "overall_score": 0.1},
    ]

    picked, weights = build_album_weights([r1, r2, r3], rows)

    assert picked == [r1, r2, r3]
    assert weights == [0.6, 0.2, 0.2]


def test_build_album_weights_uses_ranked_row_order_not_reviews_order() -> None:
    r1, r2 = _review(1), _review(2)
    reviews_chrono = [r1, r2]
    rows = [
        {"review": r2, "overall_score": 1.0},
        {"review": r1, "overall_score": 3.0},
    ]

    picked, weights = build_album_weights(reviews_chrono, rows)

    assert picked == [r2, r1]
    assert weights == [0.25, 0.75]


def test_build_playlist_candidates_weighted_sampling_matches_scores() -> None:
    """With a always-successful resolver, album counts follow weights (approx.)."""
    r1 = _review(1, tracks=[Track(1, f"A{i}", is_highlight=True) for i in range(300)])
    r2 = _review(2, tracks=[Track(1, f"B{i}", is_highlight=True) for i in range(300)])
    r3 = _review(3, tracks=[Track(1, f"C{i}", is_highlight=True) for i in range(300)])
    rows = [
        {"review": r1, "overall_score": 0.3},
        {"review": r2, "overall_score": 0.1},
        {"review": r3, "overall_score": 0.1},
    ]
    picked, weights = build_album_weights([r1, r2, r3], rows)
    assert weights == [0.6, 0.2, 0.2]

    seq = iter(range(10_000))

    def resolve(**_: object) -> str:
        return f"spotify:track:{next(seq):05d}"

    rng = random.Random(42_001)
    items = build_playlist_candidates(
        reviews=picked,
        weights=weights,
        target_count=600,
        rng=rng,
        resolve_fn=resolve,
        max_attempt_factor=30,
    )
    assert len(items) == 600
    counts = Counter(c.review_id for c in items)
    assert abs(counts[1] / 600 - 0.6) < 0.12
    assert abs(counts[2] / 600 - 0.2) < 0.12
    assert abs(counts[3] / 600 - 0.2) < 0.12


def test_candidate_tracks_for_review_matches_highlights_by_name() -> None:
    review = _review(
        1,
        tracks=[Track(1, "A"), Track(2, "B"), Track(3, "C")],
        highlights=["b"],
    )

    highlights, non_highlights = candidate_tracks_for_review(review)

    assert [t.title for t in highlights] == ["B"]
    assert [t.title for t in non_highlights] == ["A", "C"]


def test_pick_track_title_prefers_highlight_then_fallback() -> None:
    review = _review(
        1,
        tracks=[
            Track(1, "Hit", is_highlight=True),
            Track(2, "Other", is_highlight=False),
        ],
    )
    rng = random.Random(7)

    first_pick = pick_track_title_for_iteration(
        review,
        already_picked_keys=set(),
        rng=rng,
    )
    second_pick = pick_track_title_for_iteration(
        review,
        already_picked_keys={"artist::hit"},
        rng=rng,
    )

    assert first_pick == ("Hit", "highlight")
    assert second_pick == ("Other", "fallback")


def test_resolve_track_uri_strict_with_one_result() -> None:
    client = MagicMock()
    client.search_tracks.return_value = [
        SpotifyTrack(
            id="1",
            name="Track X",
            uri="spotify:track:1",
            artists=("Artist X",),
        )
    ]

    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Artist X",
        track_title="Track X",
    )

    assert uri == "spotify:track:1"


def test_resolve_track_uri_strict_picks_first_when_multiple_same_title() -> None:
    """Several API rows can match; we keep the first (duplicate listings)."""
    client = MagicMock()
    client.search_tracks.return_value = [
        SpotifyTrack("1", "Song", "spotify:track:1", ("Artist",)),
        SpotifyTrack("2", "Song", "spotify:track:2", ("Artist",)),
    ]

    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Artist",
        track_title="Song",
    )

    assert uri == "spotify:track:1"


def test_resolve_track_uri_strict_matches_title_with_umlaut_vs_ascii_spotify() -> None:
    """Review uses umlauts; Spotify title uses ASCII; folding aligns them."""
    track = SpotifyTrack(
        "99",
        "Ma vu fu",
        "spotify:track:99",
        ("Sibylle Kefer",),
    )
    client = MagicMock()
    client.search_tracks.side_effect = [[], [], [], [track]]

    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Sibylle Kefer",
        track_title="Ma vü fü",
    )

    assert uri == "spotify:track:99"
    assert client.search_tracks.call_count >= 4


def test_spotify_resolve_query_variants_includes_folded_and_loose() -> None:
    variants = spotify_resolve_query_variants("Müller Band", "Ma vü fü")
    assert variants[0] == 'artist:"Müller Band" track:"Ma vü fü"'
    assert any("Muller" in v and "Ma vu fu" in v for v in variants)
    assert any(v == "Müller Band Ma vü fü" for v in variants)


def test_spotify_resolve_query_variants_adds_feat_stripped_track_shape() -> None:
    variants = spotify_resolve_query_variants(
        "Philine Sonny",
        "Back then (I was something) (feat. Brockhoff & Shelter Boy)",
    )
    assert any('track:"Back then (I was something)"' in v for v in variants)


def test_strip_trailing_feat_credit_suffixes_keeps_non_feat_parentheses() -> None:
    raw = "Back then (I was something) (feat. Brockhoff & Shelter Boy)"
    assert _strip_trailing_feat_credit_suffixes(raw) == "Back then (I was something)"


def test_titles_match_when_feat_credit_text_differs_but_base_same() -> None:
    review = "Love in exile (feat. Michael McDonald & Kenny Loggins)"
    spotify = "Love In Exile (feat. Michael McDonald)"  # shorter credit on Spotify
    assert _titles_match_review_vs_spotify(review, spotify)


def test_titles_match_remix_paren_vs_spotify_dash_suffix() -> None:
    review = "Empathetic response (Lanark Artefak remix)"
    spotify = "Empathetic Response - Lanark Artefak Remix"
    assert _titles_match_review_vs_spotify(review, spotify)


def test_titles_match_extra_review_prefix_before_spotify_title() -> None:
    assert _titles_match_review_vs_spotify("(Oh) My sirenhead", "Sirenhead")


def test_artist_matches_slashed_review_against_single_spotify_artist_string() -> None:
    assert _artist_matches_review_vs_spotify(
        "La Petite Mort / Little Death",
        ("La petite mort/little death",),
    )


def test_spotify_resolve_query_variants_includes_remix_stripped_track() -> None:
    variants = spotify_resolve_query_variants(
        "Nine Inch Nails",
        "Empathetic response (Lanark Artefak remix)",
    )
    assert any('track:"Empathetic response"' in v for v in variants)


def test_spotify_resolve_query_variants_includes_slashed_artist_segments() -> None:
    variants = spotify_resolve_query_variants(
        "La Petite Mort / Little Death",
        "Sirenhead",
    )
    assert any('artist:"Little Death"' in v for v in variants)
    assert any('artist:"La Petite Mort"' in v for v in variants)


def test_resolve_track_uri_strict_remix_paren_to_dash_spotify_title() -> None:
    client = MagicMock()
    client.search_tracks.return_value = [
        SpotifyTrack(
            "1",
            "Empathetic Response - Lanark Artefak Remix",
            "spotify:track:1",
            ("Nine Inch Nails",),
        ),
    ]
    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Nine Inch Nails",
        track_title="Empathetic response (Lanark Artefak remix)",
    )
    assert uri == "spotify:track:1"


def test_resolve_track_uri_strict_slashed_artist_and_shorter_spotify_title() -> None:
    client = MagicMock()
    client.search_tracks.return_value = [
        SpotifyTrack(
            "2",
            "Sirenhead",
            "spotify:track:2",
            ("La petite mort/little death",),
        ),
    ]
    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="La Petite Mort / Little Death",
        track_title="(Oh) My sirenhead",
    )
    assert uri == "spotify:track:2"


def test_resolve_track_uri_strict_spotify_title_without_feat_still_matches() -> None:
    """Review lists plattentests-style feat.; Spotify row uses primary title only."""
    client = MagicMock()
    client.search_tracks.return_value = [
        SpotifyTrack(
            "1",
            "Back Then (I Was Something)",
            "spotify:track:1",
            ("Philine Sonny",),
        ),
    ]

    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Philine Sonny",
        track_title="Back then (I was something) (feat. Brockhoff & Shelter Boy)",
    )

    assert uri == "spotify:track:1"


def test_resolve_track_uri_strict_logs_warning_when_search_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.WARNING,
        logger="music_review.dashboard.newest_spotify_playlist",
    )
    client = MagicMock()
    client.search_tracks.return_value = []

    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Artist X",
        track_title="Song Y",
    )

    assert uri is None
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "no results after" in joined.lower()


def test_build_playlist_candidates_stops_when_attempt_limit_is_reached() -> None:
    review = _review(
        1,
        artist="Artist",
        album="Album",
        tracks=[Track(1, "Song A", is_highlight=True)],
    )

    items = build_playlist_candidates(
        reviews=[review],
        weights=[1.0],
        target_count=3,
        rng=random.Random(1),
        resolve_fn=lambda **_: None,
        max_attempt_factor=2,
    )

    assert items == []
