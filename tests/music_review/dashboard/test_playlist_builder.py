from __future__ import annotations

import random
from collections import Counter

import pytest

from music_review.dashboard.playlist_builder import (
    album_spread_limits,
    allocate_stratified_slot_counts,
    amplify_preference_weights,
    build_album_weights,
    build_graduated_caps_by_pool_index,
    build_playlist_suggestions,
    build_stratified_slot_plans,
    candidate_tracks_for_review,
    catalog_lookup_key,
    next_album_index_with_unused_tracks_cyclic,
    pick_track_title_for_iteration,
    primary_review_label,
    review_has_unused_track_candidate,
    weighted_sample_album_indices_without_replacement,
)
from music_review.domain.models import Review, Track


def _review(
    review_id: int,
    *,
    artist: str = "Artist",
    album: str = "Album",
    tracks: list[Track] | None = None,
    highlights: list[str] | None = None,
    labels: list[str] | None = None,
    release_year: int | None = 2024,
) -> Review:
    return Review(
        id=review_id,
        url=f"https://example.org/{review_id}",
        artist=artist,
        album=album,
        text="text",
        tracklist=tracks or [],
        highlights=highlights or [],
        labels=labels or [],
        release_year=release_year,
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
    import music_review.dashboard.playlist_builder as nsp

    artist = "Foo / Bar"
    title = "Song (live)"
    assert catalog_lookup_key(artist, title) == (
        f"{nsp._norm_text(artist)}::{nsp._norm_text(title)}"
    )


def test_catalog_lookup_key_empty_strings() -> None:
    assert catalog_lookup_key("", "") == "::"


def test_build_playlist_suggestions_stratified_counts_match_quotas() -> None:
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

    rng = random.Random(42_001)
    items = build_playlist_suggestions(
        reviews=picked,
        weights=weights,
        raw_scores=raw_scores,
        target_count=target,
        rng=rng,
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


def test_build_playlist_suggestions_returns_empty_on_weight_length_mismatch() -> None:
    r = _review(1, tracks=[Track(1, "A", is_highlight=True)])
    items = build_playlist_suggestions(
        reviews=[r],
        weights=[1.0, 1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
    )
    assert items == []


def test_build_playlist_suggestions_empty_on_score_length_mismatch() -> None:
    r = _review(1, tracks=[Track(1, "A", is_highlight=True)])
    items = build_playlist_suggestions(
        reviews=[r],
        weights=[1.0],
        raw_scores=[1.0, 1.0],
        target_count=1,
        rng=random.Random(0),
    )
    assert items == []


def test_build_playlist_suggestions_fills_at_most_one_unique_track() -> None:
    review = _review(
        1,
        artist="Artist",
        album="Album",
        tracks=[Track(1, "Song A", is_highlight=True)],
    )

    items = build_playlist_suggestions(
        reviews=[review],
        weights=[1.0],
        raw_scores=[1.0],
        target_count=3,
        rng=random.Random(1),
        max_attempt_factor=2,
    )

    assert len(items) == 1


def test_weighted_sample_returns_empty_for_zero_target_count() -> None:
    rng = random.Random(0)
    assert weighted_sample_album_indices_without_replacement([0.5, 0.5], 0, rng) == []


def test_weighted_sample_picks_distinct_indices_when_target_le_n() -> None:
    weights = [0.4, 0.3, 0.2, 0.1]
    rng = random.Random(123)
    picked = weighted_sample_album_indices_without_replacement(weights, 3, rng)
    assert len(picked) == 3
    assert len(set(picked)) == 3


def test_build_playlist_suggestions_weighted_sample_picks_distinct_albums() -> None:
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
    items = build_playlist_suggestions(
        reviews=reviews_pool,
        weights=weights,
        raw_scores=raw_scores,
        target_count=target,
        rng=random.Random(99),
        selection_strategy="weighted_sample",
    )
    assert len(items) == target
    counts = Counter(c.review_id for c in items)
    assert all(v == 1 for v in counts.values())


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


def test_build_playlist_suggestions_abandons_bad_album_and_keeps_good() -> None:
    """Skip albums without tracks and fill slots from the rest of the pool."""
    r_bad = _review(
        1,
        artist="Bad Artist",
        tracks=[],
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

    items = build_playlist_suggestions(
        reviews=[r_bad, r_ok],
        weights=weights,
        raw_scores=[1.0, 1.0],
        target_count=2,
        rng=random.Random(0),
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


def test_album_spread_limits_match_product_presets() -> None:
    assert album_spread_limits("variety", target_count=30).max_tracks_per_album == 1
    assert album_spread_limits("balanced", target_count=30).max_tracks_per_album == 3
    deep = album_spread_limits("deep", target_count=12)
    assert deep.max_tracks_per_album == 4


def test_build_graduated_caps_deep_favours_top_albums() -> None:
    caps = build_graduated_caps_by_pool_index("deep", [0.5, 0.3, 0.2, 0.1])
    assert caps[0] == 4
    assert caps[1] == 4
    assert caps[2] == 3
    assert caps[3] == 3


def test_build_graduated_caps_balanced_is_softer_than_deep() -> None:
    weights = [0.25, 0.25, 0.25, 0.25]
    balanced = build_graduated_caps_by_pool_index("balanced", weights)
    deep = build_graduated_caps_by_pool_index("deep", weights)
    assert sum(balanced.values()) <= sum(deep.values())


def test_primary_review_label_returns_first_non_empty_label() -> None:
    review = _review(1, labels=["", "Domino"])
    assert primary_review_label(review) == "Domino"


def test_build_playlist_suggestions_variety_caps_tracks_per_album() -> None:
    reviews = [
        _review(
            review_id,
            tracks=[Track(1, f"T{index}", is_highlight=True) for index in range(5)],
        )
        for review_id in range(1, 5)
    ]
    items = build_playlist_suggestions(
        reviews=reviews,
        weights=[0.25, 0.25, 0.25, 0.25],
        raw_scores=[1.0, 1.0, 1.0, 1.0],
        target_count=8,
        rng=random.Random(7),
        selection_strategy="stratified",
        album_spread_mode="variety",
    )
    counts = Counter(item.review_id for item in items)
    assert all(count <= 1 for count in counts.values())


def test_build_playlist_suggestions_deep_graduated_fills_large_targets() -> None:
    reviews = [
        _review(
            review_id,
            artist=f"Artist {review_id}",
            tracks=[
                Track(track_no, f"T{review_id}_{track_no}", is_highlight=True)
                for track_no in range(1, 9)
            ],
        )
        for review_id in range(1, 37)
    ]
    items = build_playlist_suggestions(
        reviews=reviews,
        weights=[1.0 / 36] * 36,
        raw_scores=[1.0] * 36,
        target_count=36,
        rng=random.Random(21),
        selection_strategy="stratified",
        album_spread_mode="deep",
    )
    counts = Counter(item.review_id for item in items)
    assert len(items) == 36
    assert max(counts.values()) <= 4
    assert len(counts) > 3


def test_build_playlist_suggestions_deep_limits_album_breadth_and_depth() -> None:
    reviews = [
        _review(
            review_id,
            artist=f"Artist {review_id}",
            tracks=[
                Track(index + 1, f"T{review_id}_{index}", is_highlight=True)
                for index in range(6)
            ],
        )
        for review_id in range(1, 7)
    ]
    items = build_playlist_suggestions(
        reviews=reviews,
        weights=[0.35, 0.2, 0.15, 0.12, 0.1, 0.08],
        raw_scores=[0.9, 0.7, 0.6, 0.5, 0.4, 0.3],
        target_count=12,
        rng=random.Random(11),
        selection_strategy="stratified",
        album_spread_mode="deep",
    )
    counts = Counter(item.review_id for item in items)
    assert len(items) == 12
    assert all(count <= 4 for count in counts.values())
    assert max(counts.values()) >= 3


def test_build_playlist_suggestions_includes_review_metadata() -> None:
    review = _review(
        1,
        tracks=[
            Track(1, "One", is_highlight=True),
            Track(2, "Two", is_highlight=True),
        ],
        labels=["4AD"],
        release_year=2018,
    )
    items = build_playlist_suggestions(
        reviews=[review],
        weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(3),
    )
    assert len(items) == 1
    assert items[0].release_year == 2018
    assert items[0].label == "4AD"
