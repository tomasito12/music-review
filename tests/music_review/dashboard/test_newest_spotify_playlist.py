from __future__ import annotations

import logging
import random
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.newest_spotify_playlist import (
    _artist_matches_review_vs_spotify,
    _strip_trailing_feat_credit_suffixes,
    _titles_match_review_vs_spotify,
    allocate_stratified_slot_counts,
    amplify_preference_weights,
    build_album_weights,
    build_playlist_candidates,
    build_stratified_slot_plans,
    candidate_tracks_for_review,
    catalog_lookup_key,
    next_album_index_with_unused_tracks_cyclic,
    pick_track_title_for_iteration,
    resolve_track_uri_strict,
    review_has_unused_track_candidate,
    spotify_resolve_query_variants,
    weighted_sample_album_indices_without_replacement,
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

    picked, weights, raw_scores = build_album_weights(reviews, rows)

    assert picked == reviews
    assert weights == [0.25, 0.75]
    assert raw_scores == [2.0, 6.0]


def test_build_album_weights_without_ranking_is_uniform() -> None:
    reviews = [_review(1), _review(2), _review(3)]

    picked, weights, raw_scores = build_album_weights(reviews, None)

    assert picked == reviews
    assert weights == [1 / 3, 1 / 3, 1 / 3]
    assert raw_scores == [1.0, 1.0, 1.0]


def test_build_album_weights_three_scores_match_relative_probabilities() -> None:
    """Scores 0.3, 0.1, 0.1 normalize to 3/5, 1/5, 1/5 (user-facing example)."""
    r1, r2, r3 = _review(1), _review(2), _review(3)
    rows = [
        {"review": r1, "overall_score": 0.3},
        {"review": r2, "overall_score": 0.1},
        {"review": r3, "overall_score": 0.1},
    ]

    picked, weights, raw_scores = build_album_weights([r1, r2, r3], rows)

    assert picked == [r1, r2, r3]
    assert weights == [0.6, 0.2, 0.2]
    assert raw_scores == [0.3, 0.1, 0.1]


def test_build_album_weights_uses_ranked_row_order_not_reviews_order() -> None:
    r1, r2 = _review(1), _review(2)
    reviews_chrono = [r1, r2]
    rows = [
        {"review": r2, "overall_score": 1.0},
        {"review": r1, "overall_score": 3.0},
    ]

    picked, weights, raw_scores = build_album_weights(reviews_chrono, rows)

    assert picked == [r2, r1]
    assert weights == [0.25, 0.75]
    assert raw_scores == [1.0, 3.0]


def test_amplify_preference_weights_squares_and_renormalizes() -> None:
    out = amplify_preference_weights([0.6, 0.2, 0.2], exponent=2.0)
    assert sum(out) == pytest.approx(1.0)
    assert out[0] > 0.6
    assert out[1] < 0.2
    assert out[0] == pytest.approx(0.36 / 0.44)


def test_amplify_preference_weights_cubes_and_renormalizes() -> None:
    out = amplify_preference_weights([0.6, 0.2, 0.2], exponent=3.0)
    assert sum(out) == pytest.approx(1.0)
    assert out[0] == pytest.approx(0.216 / (0.216 + 0.008 + 0.008))


def test_amplify_preference_weights_cube_favors_top_more_than_square() -> None:
    linear = [0.6, 0.2, 0.2]
    squared = amplify_preference_weights(linear, exponent=2.0)
    cubed = amplify_preference_weights(linear, exponent=3.0)
    assert cubed[0] > squared[0]


def test_amplify_preference_weights_uniform_stays_uniform() -> None:
    w = [1 / 3, 1 / 3, 1 / 3]
    out = amplify_preference_weights(w, exponent=2.0)
    assert out[0] == pytest.approx(1 / 3)


def test_amplify_preference_weights_noop_when_exponent_at_most_one() -> None:
    w = [0.5, 0.3, 0.2]
    assert amplify_preference_weights(w, exponent=1.0) == w
    assert amplify_preference_weights(w, exponent=0.5) == w


def test_amplify_preference_weights_increases_top_album_quota() -> None:
    """Convex weights allocate more slots to the highest linear-weight album."""
    linear = [0.6, 0.2, 0.2]
    boosted = amplify_preference_weights(linear, exponent=2.0)
    q_linear = allocate_stratified_slot_counts(linear, 10)
    q_boosted = allocate_stratified_slot_counts(boosted, 10)
    assert q_linear == [6, 2, 2]
    assert q_boosted[0] > q_linear[0]


def test_allocate_stratified_slot_counts_matches_largest_remainder() -> None:
    assert allocate_stratified_slot_counts([0.6, 0.2, 0.2], 10) == [6, 2, 2]
    assert allocate_stratified_slot_counts([0.6, 0.2, 0.2], 11) == [7, 2, 2]
    assert sum(allocate_stratified_slot_counts([0.1, 0.2, 0.7], 100)) == 100


def test_build_stratified_slot_plans_quotas_match_allocate() -> None:
    weights_sets = (
        [0.6, 0.2, 0.2],
        [0.0, 0.0, 0.0],
        [0.1, 0.2, 0.7],
    )
    for weights in weights_sets:
        for tc in (0, 1, 10, 11, 100):
            plans = build_stratified_slot_plans(weights, tc)
            assert [p.quota for p in plans] == allocate_stratified_slot_counts(
                weights,
                tc,
            )
            for p in plans:
                assert p.quota == p.floor_slots + p.remainder_extra_slots


def test_build_stratified_slot_plans_exposes_largest_remainder_steps() -> None:
    plans = build_stratified_slot_plans([0.6, 0.2, 0.2], 11)
    assert plans[0].ideal_slots == pytest.approx(6.6)
    assert plans[0].floor_slots == 6
    assert plans[0].remainder_extra_slots == 1
    assert plans[0].quota == 7
    assert plans[1].ideal_slots == pytest.approx(2.2)
    assert plans[1].floor_slots == 2
    assert plans[1].remainder_extra_slots == 0
    assert plans[1].quota == 2


def test_allocate_stratified_slot_counts_even_split_when_weights_zero() -> None:
    assert allocate_stratified_slot_counts([0.0, 0.0, 0.0], 10) == [4, 3, 3]


def test_catalog_lookup_key_matches_norm_text_pair() -> None:
    """``catalog_lookup_key`` must stay aligned with playlist duplicate-key logic."""
    import music_review.dashboard.newest_spotify_playlist as nsp

    artist = "Foo / Bar"
    title = "Song (live)"
    assert catalog_lookup_key(artist, title) == (
        f"{nsp._norm_text(artist)}::{nsp._norm_text(title)}"
    )


def test_catalog_lookup_key_empty_strings() -> None:
    assert catalog_lookup_key("", "") == "::"


def test_build_playlist_candidates_stratified_counts_match_quotas() -> None:
    """With a always-successful resolver, each album appears exactly quota times."""
    n_tracks = 80
    r1 = _review(
        1,
        tracks=[Track(1, f"A{i}", is_highlight=True) for i in range(n_tracks)],
    )
    r2 = _review(
        2,
        tracks=[Track(1, f"B{i}", is_highlight=True) for i in range(n_tracks)],
    )
    r3 = _review(
        3,
        tracks=[Track(1, f"C{i}", is_highlight=True) for i in range(n_tracks)],
    )
    rows = [
        {"review": r1, "overall_score": 0.3},
        {"review": r2, "overall_score": 0.1},
        {"review": r3, "overall_score": 0.1},
    ]
    picked, weights, raw_scores = build_album_weights([r1, r2, r3], rows)
    assert weights == [0.6, 0.2, 0.2]
    assert raw_scores == [0.3, 0.1, 0.1]
    target = 60
    expected = allocate_stratified_slot_counts(weights, target)
    assert expected == [36, 12, 12]

    seq = iter(range(10_000))

    def resolve(**_: object) -> str:
        return f"spotify:track:{next(seq):05d}"

    rng = random.Random(42_001)
    items = build_playlist_candidates(
        reviews=picked,
        weights=weights,
        raw_scores=raw_scores,
        target_count=target,
        rng=rng,
        resolve_fn=resolve,
        max_attempt_factor=30,
    )
    assert len(items) == target
    counts = Counter(c.review_id for c in items)
    assert counts[1] == 36
    assert counts[2] == 12
    assert counts[3] == 12
    for c in items:
        if c.review_id == 1:
            assert c.raw_score == 0.3
            assert c.score_weight == 0.6
            assert c.playlist_slot_quota == 36
            assert c.strat_ideal_slots == pytest.approx(36.0)
            assert c.strat_floor_slots == 36
            assert c.strat_remainder_extra_slots == 0
            break


def test_build_playlist_candidates_returns_empty_on_weight_length_mismatch() -> None:
    r = _review(1, tracks=[Track(1, "A", is_highlight=True)])
    items = build_playlist_candidates(
        reviews=[r],
        weights=[1.0, 1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolve_fn=lambda **_: "spotify:track:1",
    )
    assert items == []


def test_build_playlist_candidates_returns_empty_on_raw_score_length_mismatch() -> None:
    r = _review(1, tracks=[Track(1, "A", is_highlight=True)])
    items = build_playlist_candidates(
        reviews=[r],
        weights=[1.0],
        raw_scores=[1.0, 1.0],
        target_count=1,
        rng=random.Random(0),
        resolve_fn=lambda **_: "spotify:track:1",
    )
    assert items == []


def test_candidate_tracks_for_review_matches_highlights_by_name() -> None:
    review = _review(
        1,
        tracks=[Track(1, "A"), Track(2, "B"), Track(3, "C")],
        highlights=["b"],
    )

    highlights, non_highlights = candidate_tracks_for_review(review)

    assert [t.title for t in highlights] == ["B"]
    assert [t.title for t in non_highlights] == ["A", "C"]


def test_review_has_unused_track_candidate_false_when_no_tracks() -> None:
    review = _review(1, tracks=[])

    assert review_has_unused_track_candidate(review, set()) is False


def test_review_has_unused_track_candidate_true_when_track_not_picked() -> None:
    review = _review(
        1,
        artist="A",
        tracks=[Track(1, "One", is_highlight=True)],
    )

    assert review_has_unused_track_candidate(review, set()) is True


def test_next_album_index_cyclic_returns_none_for_single_album_pool() -> None:
    r = _review(1, tracks=[Track(1, "A", is_highlight=True)])

    assert (
        next_album_index_with_unused_tracks_cyclic(
            [r],
            after_index=0,
            skip_indices=set(),
            picked_song_keys=set(),
        )
        is None
    )


def test_next_album_index_cyclic_skips_dead_and_picks_next_with_track() -> None:
    a = _review(1, artist="A", tracks=[Track(1, "x", is_highlight=True)])
    b = _review(2, artist="B", tracks=[Track(1, "y", is_highlight=True)])
    reviews = [a, b]

    nxt = next_album_index_with_unused_tracks_cyclic(
        reviews,
        after_index=0,
        skip_indices={0},
        picked_song_keys=set(),
    )
    assert nxt == 1


def test_next_album_index_cyclic_respects_picked_keys() -> None:
    a = _review(1, artist="A", tracks=[Track(1, "x", is_highlight=True)])
    b = _review(2, artist="B", tracks=[Track(1, "y", is_highlight=True)])
    reviews = [a, b]

    nxt = next_album_index_with_unused_tracks_cyclic(
        reviews,
        after_index=0,
        skip_indices=set(),
        picked_song_keys={"b::y"},
    )
    assert nxt is None


def test_review_has_unused_track_candidate_false_when_all_picked() -> None:
    review = _review(
        1,
        artist="A",
        tracks=[Track(1, "One", is_highlight=True)],
    )
    keys = {"a::one"}

    assert review_has_unused_track_candidate(review, keys) is False


def test_build_playlist_candidates_abandons_bad_album_and_keeps_good() -> None:
    """Do not block the queue when the first stratified slot never resolves."""
    r_bad = _review(
        1,
        artist="Bad Artist",
        tracks=[Track(1, "X", is_highlight=True)],
    )
    r_ok = _review(
        2,
        artist="Good Artist",
        tracks=[
            Track(1, "Y1", is_highlight=True),
            Track(2, "Y2", is_highlight=True),
        ],
    )
    weights = [0.5, 0.5]
    assert allocate_stratified_slot_counts(weights, 2) == [1, 1]

    def resolve(*, artist: str, track_title: str) -> str | None:
        if artist == "Bad Artist":
            return None
        return f"spotify:track:{track_title}"

    items = build_playlist_candidates(
        reviews=[r_bad, r_ok],
        weights=weights,
        raw_scores=[1.0, 1.0],
        target_count=2,
        rng=random.Random(0),
        resolve_fn=resolve,
        resolve_retries_per_album=2,
        max_attempt_factor=12,
    )

    assert len(items) == 2
    assert all(c.review_id == 2 for c in items)
    titles = {c.track_title for c in items}
    assert titles == {"Y1", "Y2"}


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
        raw_scores=[1.0],
        target_count=3,
        rng=random.Random(1),
        resolve_fn=lambda **_: None,
        max_attempt_factor=2,
    )

    assert items == []


def test_weighted_sample_returns_empty_for_zero_target_count() -> None:
    rng = random.Random(0)
    assert weighted_sample_album_indices_without_replacement([0.5, 0.5], 0, rng) == []


def test_weighted_sample_returns_empty_for_empty_weights() -> None:
    rng = random.Random(0)
    assert weighted_sample_album_indices_without_replacement([], 5, rng) == []


def test_weighted_sample_picks_distinct_indices_when_target_le_n() -> None:
    """Without replacement: every picked index must be unique and a real index."""
    weights = [0.4, 0.3, 0.2, 0.1]
    rng = random.Random(123)

    picked = weighted_sample_album_indices_without_replacement(weights, 3, rng)

    assert len(picked) == 3
    assert len(set(picked)) == 3
    assert all(0 <= i < len(weights) for i in picked)


def test_weighted_sample_only_picks_positive_weight_indices() -> None:
    """Indices with weight 0 must be excluded from the no-replacement phase."""
    weights = [0.0, 1.0, 0.0, 2.0, 0.0]
    rng = random.Random(7)

    picked = weighted_sample_album_indices_without_replacement(weights, 2, rng)

    assert sorted(picked) == [1, 3]


def test_weighted_sample_target_exceeds_positive_weights_uses_replacement() -> None:
    """When target > #positive-weight albums, fall back to with-replacement extras
    so the playlist still reaches ``target_count`` slots; only positive-weight
    albums are eligible for the extras.
    """
    weights = [0.0, 1.0, 0.0, 2.0]
    rng = random.Random(11)
    target_count = 6

    picked = weighted_sample_album_indices_without_replacement(
        weights,
        target_count,
        rng,
    )

    assert len(picked) == target_count
    counts = Counter(picked)
    assert counts[1] >= 1
    assert counts[3] >= 1
    assert counts[0] == 0
    assert counts[2] == 0


def test_weighted_sample_all_zero_weights_falls_back_to_uniform() -> None:
    """All weights zero: uniform sample without replacement, then with replacement."""
    weights = [0.0, 0.0, 0.0]
    rng = random.Random(2_024)

    picked = weighted_sample_album_indices_without_replacement(weights, 5, rng)

    assert len(picked) == 5
    assert all(0 <= i < len(weights) for i in picked)
    assert set(picked[:3]) == {0, 1, 2}


def test_weighted_sample_high_weight_dominates_in_expectation() -> None:
    """A 9:1 weight ratio should pick the dominant index >>50% of the time."""
    weights = [9.0, 1.0]
    rng = random.Random(2_026)
    n_trials = 2_000

    counts = Counter(
        weighted_sample_album_indices_without_replacement(weights, 1, rng)[0]
        for _ in range(n_trials)
    )

    assert counts[0] / n_trials > 0.7


def test_weighted_sample_every_positive_album_has_a_chance_in_large_pool() -> None:
    """The motivating bug: with 1000 albums and target 30, *every* album must be
    pickable across enough trials -- not just the top 30 (the deterministic
    largest-remainder failure mode).
    """
    n = 1_000
    weights = [(i + 1) / n for i in range(n)]
    rng = random.Random(5_000)
    bottom_quartile = set(range(n // 4))
    appeared: set[int] = set()

    for _ in range(200):
        picks = weighted_sample_album_indices_without_replacement(weights, 30, rng)
        appeared.update(picks)

    assert appeared & bottom_quartile, (
        "Bottom-quartile albums never appeared across 200 draws; the sampler "
        "is acting like a deterministic top-N selector."
    )


def test_build_playlist_candidates_weighted_sample_picks_distinct_albums() -> None:
    """In archive mode (target <= n) every chosen album must appear at most once."""
    n_albums = 8
    reviews_pool = [
        _review(
            i + 1,
            tracks=[Track(1, f"T{i}_{j}", is_highlight=True) for j in range(3)],
        )
        for i in range(n_albums)
    ]
    weights = [1.0 / n_albums] * n_albums
    raw_scores = [1.0] * n_albums
    target = 5
    seq = iter(range(10_000))

    items = build_playlist_candidates(
        reviews=reviews_pool,
        weights=weights,
        raw_scores=raw_scores,
        target_count=target,
        rng=random.Random(99),
        resolve_fn=lambda **_: f"spotify:track:{next(seq):05d}",
        selection_strategy="weighted_sample",
    )

    assert len(items) == target
    counts = Counter(c.review_id for c in items)
    assert all(v == 1 for v in counts.values())


def test_build_playlist_candidates_weighted_sample_lets_low_score_album_appear() -> (
    None
):
    """Even with a 30:1 weight ratio, the low-weight album must reach the
    playlist eventually; the deterministic largest-remainder allocator would
    drop it entirely when target is small.
    """
    high = _review(
        1,
        tracks=[Track(1, f"H{i}", is_highlight=True) for i in range(20)],
    )
    low = _review(
        2,
        tracks=[Track(1, f"L{i}", is_highlight=True) for i in range(20)],
    )
    weights = [30 / 31, 1 / 31]
    raw_scores = [3.0, 0.1]
    target = 2
    n_trials = 60
    saw_low = False

    def _make_resolver(seq: Iterator[int]) -> Callable[..., str]:
        def _resolve(**_: object) -> str:
            return f"spotify:track:{next(seq):05d}"

        return _resolve

    for trial in range(n_trials):
        items = build_playlist_candidates(
            reviews=[high, low],
            weights=weights,
            raw_scores=raw_scores,
            target_count=target,
            rng=random.Random(7_000 + trial),
            resolve_fn=_make_resolver(iter(range(10_000))),
            selection_strategy="weighted_sample",
        )
        ids = {c.review_id for c in items}
        assert ids <= {1, 2}
        if 2 in ids:
            saw_low = True
            break

    assert saw_low, (
        "Low-weight album never appeared across the trial budget; weighted "
        "sampling is collapsing into a deterministic top-N selection."
    )
