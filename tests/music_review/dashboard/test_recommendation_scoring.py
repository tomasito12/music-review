"""Tests for recommendation overall-score helpers."""

from __future__ import annotations

import random

import pytest

from music_review.dashboard.recommendation_scoring import (
    affinity_vector_from_entries,
    album_spectrum_term_from_style_breadth,
    album_style_breadth_norm_for_review_ids,
    blend_purity_breadth,
    breadth_raw_from_selected_community_masses,
    community_spectrum_norm_batch,
    cosine_fit_from_affinity_entries,
    cosine_similarity_sparse,
    effective_plattentests_rating,
    effective_style_count_from_proportions,
    effective_style_diversity_from_affinity_entries,
    gated_community_spectrum,
    gini_coefficient,
    global_album_style_breadth_norm_by_review_id,
    matching_style_breadth_from_affinity_entries,
    normalize_coverage_batch,
    overall_score,
    percentile_rank_normalize_batch,
    purity_max_weighted_share,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
    spectrum_matching_gate,
    style_fit_batch_normalized,
    weighted_style_fit_raw,
)


def test_normalize_coverage_batch_spread() -> None:
    assert normalize_coverage_batch([0.0, 0.5, 1.0]) == [0.0, 0.5, 1.0]


def test_normalize_coverage_batch_all_equal() -> None:
    assert normalize_coverage_batch([0.3, 0.3, 0.3]) == [1.0, 1.0, 1.0]


def test_normalize_coverage_batch_empty() -> None:
    assert normalize_coverage_batch([]) == []


def test_effective_rating_missing() -> None:
    assert effective_plattentests_rating(None, default_when_missing=7.0) == 7.0


def test_rating_to_unit_interval_default() -> None:
    assert rating_to_unit_interval(None, default_on_10_scale=7.0) == pytest.approx(0.7)


def test_rating_to_unit_interval_clamp() -> None:
    assert rating_to_unit_interval(11.0, default_on_10_scale=7.0) == 1.0
    assert rating_to_unit_interval(-1.0, default_on_10_scale=7.0) == 0.0


def test_purity_max_weighted_share() -> None:
    assert purity_max_weighted_share(0.8, 1.0) == pytest.approx(0.8)
    assert purity_max_weighted_share(0.5, 1.0) == pytest.approx(0.5)
    assert purity_max_weighted_share(1.0, 0.0) == 0.0


def test_cosine_similarity_sparse_orthogonal() -> None:
    left = {"A": 1.0}
    right = {"B": 1.0}
    assert cosine_similarity_sparse(left, right) == pytest.approx(0.0)


def test_cosine_similarity_sparse_identical() -> None:
    vector = {"A": 0.6, "B": 0.8}
    assert cosine_similarity_sparse(vector, vector) == pytest.approx(1.0)


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


def test_cosine_fit_alias_matches_weighted_style_fit() -> None:
    entries = [{"id": "C001", "score": 0.5}, {"id": "C999", "score": 0.5}]
    kwargs = {
        "selected_comms": {"C001"},
        "weights_raw": {"C001": 1.0},
    }
    assert cosine_fit_from_affinity_entries(entries, **kwargs) == pytest.approx(
        weighted_style_fit_raw(entries, **kwargs),
    )


def test_effective_style_count_single_style_is_one() -> None:
    assert effective_style_count_from_proportions((1.0,)) == pytest.approx(1.0)


def test_effective_style_count_fifty_fifty_is_two() -> None:
    assert effective_style_count_from_proportions((0.5, 0.5)) == pytest.approx(2.0)


def test_effective_style_diversity_pure_album_is_one() -> None:
    assert effective_style_count_from_proportions((1.0,)) == pytest.approx(1.0)
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


def test_matching_style_breadth_ignores_unselected_communities() -> None:
    entries = [
        {"id": "c1", "score": 0.5},
        {"id": "c2", "score": 0.5},
        {"id": "c9", "score": 0.9},
    ]
    assert matching_style_breadth_from_affinity_entries(
        entries,
        selected_comms={"c1"},
    ) == pytest.approx(0.0)
    breadth_two_selected = matching_style_breadth_from_affinity_entries(
        entries,
        selected_comms={"c1", "c2"},
    )
    assert breadth_two_selected > 0.0


def test_matching_style_breadth_single_selected_match_is_zero() -> None:
    entries = [{"id": "c1", "score": 1.0}, {"id": "c9", "score": 0.8}]
    assert matching_style_breadth_from_affinity_entries(
        entries,
        selected_comms={"c1", "c2"},
    ) == pytest.approx(0.0)


def test_album_spectrum_term_uniform_when_all_breadths_equal() -> None:
    """Crossover shifts every equal-breadth album by the same amount."""
    pure, _, _ = album_spectrum_term_from_style_breadth(0.0, crossover_weight=0.0)
    broad, _, _ = album_spectrum_term_from_style_breadth(0.0, crossover_weight=1.0)
    assert pure > broad
    same_low, _, _ = album_spectrum_term_from_style_breadth(0.0, crossover_weight=0.2)
    same_high, _, _ = album_spectrum_term_from_style_breadth(0.0, crossover_weight=0.8)
    assert same_high < same_low


def test_affinity_vector_from_entries_ignores_invalid_rows() -> None:
    entries: list[dict[str, object]] = [
        {"id": "C001", "score": 0.7},
        {"id": "C002", "score": "bad"},
        {"score": 0.2},
    ]
    assert affinity_vector_from_entries(entries) == {"C001": 0.7}


def test_blend_purity_breadth_endpoints() -> None:
    assert blend_purity_breadth(0.9, 0.1, crossover_weight=0.0) == pytest.approx(0.9)
    assert blend_purity_breadth(0.9, 0.1, crossover_weight=1.0) == pytest.approx(0.1)
    assert blend_purity_breadth(0.5, 0.5, crossover_weight=0.5) == pytest.approx(0.5)


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


def test_percentile_rank_differs_from_min_max_when_skewed() -> None:
    """Middle value gets 0.5 by rank, not ~0.01 by min-max."""
    vals = [0.0, 0.01, 1.0]
    assert percentile_rank_normalize_batch(vals) == pytest.approx([0.0, 0.5, 1.0])
    assert normalize_coverage_batch(vals) == pytest.approx([0.0, 0.01, 1.0])


def test_community_spectrum_norm_batch_lambda_zero_is_purity_norm() -> None:
    pur = [0.2, 0.8, 0.5]
    br = [0.9, 0.1, 0.5]
    p_n, b_n, mix = community_spectrum_norm_batch(pur, br, crossover_weight=0.0)
    assert p_n == normalize_coverage_batch(pur)
    assert mix == p_n
    assert b_n == percentile_rank_normalize_batch(br)


def test_community_spectrum_norm_batch_lambda_one_is_breadth_norm() -> None:
    pur = [0.2, 0.8, 0.5]
    br = [0.9, 0.1, 0.5]
    _p_n, b_n, mix = community_spectrum_norm_batch(pur, br, crossover_weight=1.0)
    assert b_n == percentile_rank_normalize_batch(br)
    assert mix == b_n


def test_community_spectrum_norm_batch_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        community_spectrum_norm_batch([0.1], [0.1, 0.2], crossover_weight=0.5)


def test_album_spectrum_term_pure_album_favors_low_crossover() -> None:
    spectrum, purity, breadth = album_spectrum_term_from_style_breadth(
        0.0,
        crossover_weight=0.0,
    )
    assert breadth == pytest.approx(0.0)
    assert purity == pytest.approx(1.0)
    assert spectrum == pytest.approx(1.0)


def test_album_spectrum_term_broad_album_favors_high_crossover() -> None:
    spectrum, purity, breadth = album_spectrum_term_from_style_breadth(
        0.8,
        crossover_weight=1.0,
    )
    assert breadth == pytest.approx(0.8)
    assert purity == pytest.approx(0.2)
    assert spectrum == pytest.approx(0.8)


def test_album_spectrum_term_default_crossover_blends() -> None:
    spectrum, purity, breadth = album_spectrum_term_from_style_breadth(
        0.6,
        crossover_weight=0.2,
    )
    assert breadth == pytest.approx(0.6)
    assert purity == pytest.approx(0.4)
    assert spectrum == pytest.approx(0.8 * 0.4 + 0.2 * 0.6)


def test_overall_score_linear() -> None:
    o1 = overall_score(1.0, 1.0, 1.0, alpha=0.5, beta=0.25, gamma=0.25)
    assert o1 == pytest.approx(1.0)
    o2 = overall_score(0.0, 0.0, 1.0, alpha=0.5, beta=0.25, gamma=0.25)
    assert o2 == pytest.approx(0.25)


def test_spectrum_matching_gate_zero_s_a() -> None:
    assert spectrum_matching_gate(0.0, half_saturation=0.2) == pytest.approx(0.0)


def test_spectrum_matching_gate_half_at_k() -> None:
    assert spectrum_matching_gate(0.2, half_saturation=0.2) == pytest.approx(0.5)


def test_spectrum_matching_gate_disabled_when_k_non_positive() -> None:
    assert spectrum_matching_gate(0.0, half_saturation=0.0) == pytest.approx(1.0)
    assert spectrum_matching_gate(0.0, half_saturation=-1.0) == pytest.approx(1.0)


def test_gated_community_spectrum_multiplies() -> None:
    eff, g = gated_community_spectrum(0.8, 0.2, half_saturation=0.2)
    assert g == pytest.approx(0.5)
    assert eff == pytest.approx(0.4)


def test_gini_coefficient_equal_masses() -> None:
    assert gini_coefficient([1.0, 1.0, 1.0]) == pytest.approx(0.0)


def test_gini_coefficient_single_mass() -> None:
    assert gini_coefficient([5.0]) == pytest.approx(0.0)


def test_gini_coefficient_empty_or_zero() -> None:
    assert gini_coefficient([]) == pytest.approx(1.0)
    assert gini_coefficient([0.0, 0.0]) == pytest.approx(1.0)


def test_gini_coefficient_max_inequality_three() -> None:
    """One holder of all mass -> high Gini."""
    g = gini_coefficient([10.0, 0.0, 0.0])
    assert g == pytest.approx(2.0 / 3.0)


def test_breadth_raw_from_selected_equal_masses() -> None:
    raw = {"A": 1.0, "B": 1.0}
    b = breadth_raw_from_selected_community_masses(
        raw,
        {"A", "B"},
        {},
    )
    assert b == pytest.approx(1.0)


def test_breadth_raw_from_selected_concentrated() -> None:
    raw = {"A": 10.0, "B": 0.0, "C": 0.0}
    b = breadth_raw_from_selected_community_masses(
        raw,
        {"A", "B", "C"},
        {},
    )
    # Gini = 2/3 for [10,0,0] -> breadth = 1/3
    assert b == pytest.approx(1.0 / 3.0)


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


def test_breadth_raw_from_selected_user_weights() -> None:
    """High weight on empty community lowers inverted Gini breadth."""
    raw = {"A": 1.0, "B": 1.0}
    b_even = breadth_raw_from_selected_community_masses(
        raw,
        {"A", "B"},
        {"A": 1.0, "B": 1.0},
    )
    b_skew = breadth_raw_from_selected_community_masses(
        raw,
        {"A", "B"},
        {"A": 1.0, "B": 0.01},
    )
    assert b_even == pytest.approx(1.0)
    assert b_skew < b_even
