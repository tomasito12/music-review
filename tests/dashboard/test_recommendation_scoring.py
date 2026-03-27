"""Tests for recommendation overall-score helpers."""

from __future__ import annotations

import random

import pytest

from music_review.dashboard.recommendation_scoring import (
    blend_purity_breadth,
    breadth_raw_from_selected_community_masses,
    community_spectrum_norm_batch,
    effective_plattentests_rating,
    gated_community_spectrum,
    gini_coefficient,
    normalize_coverage_batch,
    overall_score,
    percentile_rank_normalize_batch,
    purity_max_weighted_share,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
    spectrum_matching_gate,
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
    p_n, b_n, mix = community_spectrum_norm_batch(
        pur, br, crossover_weight=0.0
    )
    assert p_n == normalize_coverage_batch(pur)
    assert mix == p_n
    assert b_n == percentile_rank_normalize_batch(br)


def test_community_spectrum_norm_batch_lambda_one_is_breadth_norm() -> None:
    pur = [0.2, 0.8, 0.5]
    br = [0.9, 0.1, 0.5]
    _p_n, b_n, mix = community_spectrum_norm_batch(
        pur, br, crossover_weight=1.0
    )
    assert b_n == percentile_rank_normalize_batch(br)
    assert mix == b_n


def test_community_spectrum_norm_batch_length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        community_spectrum_norm_batch([0.1], [0.1, 0.2], crossover_weight=0.5)


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
