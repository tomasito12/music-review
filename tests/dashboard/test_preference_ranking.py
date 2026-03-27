"""Tests for preference-based ranking (newest reviews / recommendations parity)."""

from __future__ import annotations

import random

from music_review.dashboard.preference_ranking import (
    global_breadth_norm_by_review_id,
    preference_ranked_rows,
    rank_reviews_by_saved_preferences,
)
from music_review.domain.models import Review


def _review(rid: int, rating: float | None = 5.0) -> Review:
    return Review(
        id=rid,
        url="",
        artist="Artist",
        album=f"Album {rid}",
        text="",
        rating=rating,
    )


def test_rank_empty_selection_returns_same_order() -> None:
    r1, r2 = _review(2), _review(1)
    incoming = [r1, r2]
    out = rank_reviews_by_saved_preferences(
        incoming,
        affinity_by_review_id={},
        memberships={},
        selected_comms=set(),
        weights_raw={},
        filter_settings={},
    )
    assert out == incoming


def test_rank_orders_by_weighted_affinity_like_recommendations() -> None:
    r_weak, r_strong = _review(10), _review(20)
    # Newest-first pool order (high id first) — ranking should pull stronger match up
    incoming = [r_weak, r_strong]
    aff = {
        10: {"communities": {"res_10": [{"id": "c1", "score": 0.1}]}},
        20: {"communities": {"res_10": [{"id": "c1", "score": 0.95}]}},
    }
    out = rank_reviews_by_saved_preferences(
        incoming,
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={"sort_mode": "Deterministisch", "serendipity": 0.0},
    )
    assert out[0].id == 20
    assert out[1].id == 10


def test_rank_keeps_no_match_reviews_but_sorts_them_lower() -> None:
    r_match, r_none = _review(2), _review(1)
    incoming = [r_none, r_match]
    aff = {
        2: {"communities": {"res_10": [{"id": "c1", "score": 0.8}]}},
    }
    out = rank_reviews_by_saved_preferences(
        incoming,
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={},
    )
    assert out[0].id == 2
    assert out[1].id == 1


def test_global_breadth_norm_by_review_id_empty_without_selection() -> None:
    r = _review(1)
    assert global_breadth_norm_by_review_id(
        [r],
        memberships={},
        selected_comms=set(),
        weights_raw={},
    ) == {}


def test_global_breadth_map_overrides_batch_breadth_norm() -> None:
    r1, r2 = _review(1), _review(2)
    aff = {
        1: {"communities": {"res_10": [{"id": "c1", "score": 0.5}]}},
        2: {"communities": {"res_10": [{"id": "c1", "score": 0.5}]}},
    }
    rows = preference_ranked_rows(
        [r1, r2],
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={},
        apply_serendipity=False,
        global_breadth_norm_by_review_id={1: 0.0, 2: 1.0},
    )
    by_id = {r["review_id"]: r["breadth_norm"] for r in rows}
    assert by_id[1] == 0.0
    assert by_id[2] == 1.0


def test_preference_ranked_rows_skips_serendipity_when_disabled() -> None:
    r_low, r_high = _review(10), _review(20)
    aff = {
        10: {"communities": {"res_10": [{"id": "c1", "score": 0.1}]}},
        20: {"communities": {"res_10": [{"id": "c1", "score": 0.95}]}},
    }
    rows = preference_ranked_rows(
        [r_low, r_high],
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={"sort_mode": "Serendipity", "serendipity": 1.0},
        apply_serendipity=False,
    )
    assert [r["review"].id for r in rows] == [20, 10]


def test_preference_ranked_rows_contains_display_keys() -> None:
    r_a, r_b = _review(100), _review(200)
    aff = {
        100: {"communities": {"res_10": [{"id": "c1", "score": 0.5}]}},
        200: {"communities": {"res_10": [{"id": "c1", "score": 0.5}]}},
    }
    rows = preference_ranked_rows(
        [r_a, r_b],
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={},
    )
    assert len(rows) == 2
    for row in rows:
        assert "review" in row
        assert "overall_score" in row
        assert "score" in row
        assert "community_spectrum_norm" in row
        assert "community_spectrum_effective" in row
        assert "spectrum_matching_gate" in row
        assert "rating_norm" in row
        assert "purity_norm" in row
        assert "breadth_norm" in row
        assert "alpha" in row and "beta" in row and "gamma" in row


def test_serendipity_zero_preserves_score_order() -> None:
    r_a, r_b = _review(100), _review(200)
    incoming = [r_a, r_b]
    aff = {
        100: {"communities": {"res_10": [{"id": "c1", "score": 0.99}]}},
        200: {"communities": {"res_10": [{"id": "c1", "score": 0.1}]}},
    }
    rng = random.Random(999)
    out = rank_reviews_by_saved_preferences(
        incoming,
        affinity_by_review_id=aff,
        memberships={},
        selected_comms={"c1"},
        weights_raw={},
        filter_settings={"sort_mode": "Serendipity", "serendipity": 0.0},
        rng=rng,
    )
    assert out[0].id == 100
    assert out[1].id == 200
