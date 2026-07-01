"""Tests for recommendation overall-score helpers."""

from __future__ import annotations

import random

import pytest

from music_review.dashboard.recommendation_scoring import (
    affinity_vector_from_entries,
    album_style_breadth_norm_for_review_ids,
    album_style_proportions_from_entries,
    effective_plattentests_rating,
    effective_style_count_from_proportions,
    effective_style_diversity_from_affinity_entries,
    global_album_style_breadth_norm_by_review_id,
    global_style_fit_norm_by_review_id,
    overall_score,
    percentile_rank_normalize_batch,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
    shannon_entropy_from_proportions,
    style_fit_batch_normalized,
    style_fit_norm_for_review_ids,
    weighted_style_fit_raw,
)


def test_effective_rating_missing() -> None:
    assert effective_plattentests_rating(None, default_when_missing=7.0) == 7.0


def test_rating_to_unit_interval_default() -> None:
    assert rating_to_unit_interval(None, default_on_10_scale=7.0) == pytest.approx(0.7)


def test_rating_to_unit_interval_clamp() -> None:
    assert rating_to_unit_interval(11.0, default_on_10_scale=7.0) == 1.0
    assert rating_to_unit_interval(-1.0, default_on_10_scale=7.0) == 0.0


def test_weighted_style_fit_all_profile_communities_at_one() -> None:
    """When every album community is in the profile at 1.0, fit is 1.0."""
    entries = [
        {"id": "Jazz", "score": 0.3},
        {"id": "PostPunk", "score": 0.6},
        {"id": "Pop", "score": 0.1},
    ]
    weights = {"Jazz": 1.0, "PostPunk": 1.0, "Pop": 1.0}
    fit = weighted_style_fit_raw(
        entries,
        selected_comms={"Jazz", "PostPunk", "Pop"},
        weights_raw=weights,
    )
    assert fit == pytest.approx(1.0)


def test_weighted_style_fit_unselected_album_communities_contribute_zero() -> None:
    """Black-metal-heavy album with only indie in profile scores low."""
    entries = [
        {"id": "BM", "score": 0.55},
        {"id": "PostMetal", "score": 0.30},
        {"id": "IndieRock", "score": 0.15},
    ]
    fit = weighted_style_fit_raw(
        entries,
        selected_comms={"IndieRock"},
        weights_raw={"IndieRock": 0.5},
    )
    assert fit == pytest.approx(0.075)


def test_weighted_style_fit_single_album_community_equals_user_weight() -> None:
    entries = [{"id": "C001", "score": 1.0}]
    assert weighted_style_fit_raw(
        entries,
        selected_comms={"C001"},
        weights_raw={"C001": 0.5},
    ) == pytest.approx(0.5)
    assert weighted_style_fit_raw(
        entries,
        selected_comms={"C001"},
        weights_raw={"C001": 1.0},
    ) == pytest.approx(1.0)


def test_weighted_style_fit_style_pure_album_ranks_higher_than_mixed() -> None:
    """Album mass only on a liked community beats a half-unwanted mix."""
    weights = {"C001": 1.0}
    pure = weighted_style_fit_raw(
        [{"id": "C001", "score": 1.0}],
        selected_comms={"C001"},
        weights_raw=weights,
    )
    mixed = weighted_style_fit_raw(
        [{"id": "C001", "score": 0.5}, {"id": "C999", "score": 0.5}],
        selected_comms={"C001"},
        weights_raw=weights,
    )
    assert pure == pytest.approx(1.0)
    assert mixed == pytest.approx(0.5)
    assert pure > mixed


def test_style_fit_batch_normalized_scales_to_max_one() -> None:
    assert style_fit_batch_normalized([0.2, 0.8, 0.5]) == pytest.approx(
        [0.25, 1.0, 0.625],
    )


def test_effective_style_count_single_style_is_one() -> None:
    assert effective_style_count_from_proportions((1.0,)) == pytest.approx(1.0)


def test_effective_style_count_fifty_fifty_is_two() -> None:
    assert effective_style_count_from_proportions((0.5, 0.5)) == pytest.approx(2.0)


def test_effective_style_diversity_pure_album_is_one() -> None:
    assert effective_style_diversity_from_affinity_entries(
        [{"id": "Rock", "score": 1.0}],
    ) == pytest.approx(1.0)


def test_global_album_style_breadth_norm_maps_extremes() -> None:
    affinities = {
        1: {
            "communities": {
                "res_10": [{"id": "c1", "score": 1.0}],
            },
        },
        2: {
            "communities": {
                "res_10": [
                    {"id": "c1", "score": 0.5},
                    {"id": "c2", "score": 0.5},
                ],
            },
        },
    }
    norms = global_album_style_breadth_norm_by_review_id(affinities)
    assert norms[1] == pytest.approx(0.0)
    assert norms[2] == pytest.approx(1.0)


def test_album_style_breadth_norm_for_review_ids_uses_global_map() -> None:
    norms = album_style_breadth_norm_for_review_ids(
        [1, 2],
        {1: 1.0, 2: 2.0},
        global_norm_by_review_id={1: 0.2, 2: 0.9},
    )
    assert norms == pytest.approx([0.2, 0.9])


def test_album_style_breadth_norm_for_review_ids_batch_fallback() -> None:
    norms = album_style_breadth_norm_for_review_ids(
        [1, 2, 3],
        {1: 1.0, 2: 2.0, 3: 3.0},
    )
    assert norms == pytest.approx([0.0, 0.5, 1.0])


def test_effective_style_diversity_fifty_fifty_is_two() -> None:
    entries = [
        {"id": "c1", "score": 0.5},
        {"id": "c2", "score": 0.5},
    ]
    diversity = effective_style_diversity_from_affinity_entries(entries)
    assert diversity == pytest.approx(2.0)


def test_effective_style_diversity_increases_with_mix_diversity() -> None:
    values = [
        effective_style_diversity_from_affinity_entries([{"id": "a", "score": 1.0}]),
        effective_style_diversity_from_affinity_entries(
            [{"id": "a", "score": 0.8}, {"id": "b", "score": 0.2}],
        ),
        effective_style_diversity_from_affinity_entries(
            [{"id": "a", "score": 0.5}, {"id": "b", "score": 0.5}],
        ),
        effective_style_diversity_from_affinity_entries(
            [
                {"id": "a", "score": 0.25},
                {"id": "b", "score": 0.25},
                {"id": "c", "score": 0.25},
                {"id": "d", "score": 0.25},
            ],
        ),
    ]
    assert values == sorted(values)


def test_effective_style_diversity_empty_entries_returns_one() -> None:
    assert effective_style_diversity_from_affinity_entries([]) == pytest.approx(1.0)


def test_affinity_vector_from_entries_ignores_invalid_rows() -> None:
    entries: list[dict[str, object]] = [
        {"id": "C001", "score": 0.7},
        {"id": "C002", "score": "bad"},
        {"score": 0.2},
    ]
    assert affinity_vector_from_entries(entries) == {"C001": 0.7}


def test_album_style_proportions_from_entries_normalizes_positive_scores() -> None:
    proportions = album_style_proportions_from_entries(
        [{"id": "a", "score": 1.0}, {"id": "b", "score": 3.0}],
    )
    assert proportions == pytest.approx((0.25, 0.75))


def test_shannon_entropy_uniform_mix_is_log_n() -> None:
    import math

    entropy = shannon_entropy_from_proportions((0.25, 0.25, 0.25, 0.25))
    assert entropy == pytest.approx(math.log(4.0))


def test_percentile_rank_normalize_batch_spread() -> None:
    assert percentile_rank_normalize_batch([0.1, 0.5, 0.9]) == pytest.approx(
        [0.0, 0.5, 1.0]
    )


def test_percentile_rank_normalize_batch_ties() -> None:
    assert percentile_rank_normalize_batch([0.5, 0.5, 1.0]) == pytest.approx(
        [0.0, 0.0, 1.0]
    )


def test_percentile_rank_normalize_batch_single() -> None:
    assert percentile_rank_normalize_batch([0.3]) == [1.0]


def test_percentile_rank_normalize_batch_all_equal() -> None:
    assert percentile_rank_normalize_batch([0.4, 0.4, 0.4]) == [1.0, 1.0, 1.0]


def test_percentile_rank_normalize_batch_empty() -> None:
    assert percentile_rank_normalize_batch([]) == []


def test_overall_score_linear() -> None:
    o1 = overall_score(1.0, 1.0, 1.0, alpha=0.5, beta=0.25, gamma=0.25)
    assert o1 == pytest.approx(1.0)
    o2 = overall_score(0.0, 0.0, 1.0, alpha=0.5, beta=0.25, gamma=0.25)
    assert o2 == pytest.approx(0.25)


def test_global_style_fit_norm_maps_extremes() -> None:
    affinities = {
        1: {"communities": {"res_10": [{"id": "c1", "score": 1.0}]}},
        2: {
            "communities": {
                "res_10": [
                    {"id": "c1", "score": 0.5},
                    {"id": "c2", "score": 0.5},
                ],
            },
        },
    }
    norms = global_style_fit_norm_by_review_id(
        affinities,
        selected_comms={"c1"},
        weights_raw={"c1": 1.0},
    )
    assert norms[1] == pytest.approx(1.0)
    assert norms[2] == pytest.approx(0.0)


def test_style_fit_norm_for_review_ids_uses_global_map() -> None:
    norms = style_fit_norm_for_review_ids(
        [1, 2],
        {1: 0.9, 2: 0.2},
        global_norm_by_review_id={1: 0.8, 2: 0.3},
    )
    assert norms == pytest.approx([0.8, 0.3])


def test_serendipity_rank_sort_key_s_zero_preserves_order() -> None:
    rng = random.Random(123)
    n = 5
    keys = [
        serendipity_rank_sort_key(
            i,
            serendipity=0.0,
            rng=rng,
            n_items=n,
        )
        for i in range(n)
    ]
    assert keys == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_serendipity_rank_sort_key_single_item() -> None:
    rng = random.Random(0)
    assert serendipity_rank_sort_key(0, serendipity=1.0, rng=rng, n_items=1) == 0.0


def test_serendipity_rank_sort_key_deterministic() -> None:
    rng = random.Random(7)
    k1 = serendipity_rank_sort_key(2, serendipity=0.5, rng=rng, n_items=10)
    rng2 = random.Random(7)
    k2 = serendipity_rank_sort_key(2, serendipity=0.5, rng=rng2, n_items=10)
    assert k1 == pytest.approx(k2)
