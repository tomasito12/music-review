"""Tests for preference-based ranking (newest reviews / recommendations parity)."""

from __future__ import annotations

import random

import pytest

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


def test_global_breadth_norm_by_review_id_empty_without_affinities() -> None:
    assert global_breadth_norm_by_review_id({}) == {}


def test_album_style_breadth_drives_breadth_norm() -> None:
    r1, r2 = _review(1), _review(2)
    aff = {
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
    album_breadth_by_id = {r["review_id"]: r["album_style_breadth"] for r in rows}
    assert by_id[1] == pytest.approx(0.0)
    assert by_id[2] > 0.0
    assert album_breadth_by_id[2] == pytest.approx(1.0)


def test_gamma_weight_reorders_by_style_breadth() -> None:
    r_pure, r_mixed = _review(1), _review(2)
    aff = {
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
    common = {
        "affinity_by_review_id": aff,
        "memberships": {},
        "selected_comms": {"c1"},
        "weights_raw": {"c1": 1.0},
        "apply_serendipity": False,
    }
    breadth_focus = preference_ranked_rows(
        [r_pure, r_mixed],
        filter_settings={
            "overall_weight_alpha": 0.0,
            "overall_weight_beta": 0.0,
            "overall_weight_gamma": 1.0,
        },
        **common,
    )
    fit_focus = preference_ranked_rows(
        [r_pure, r_mixed],
        filter_settings={
            "overall_weight_alpha": 1.0,
            "overall_weight_beta": 0.0,
            "overall_weight_gamma": 0.0,
        },
        **common,
    )
    assert [row["review_id"] for row in breadth_focus] == [2, 1]
    assert [row["review_id"] for row in fit_focus] == [1, 2]


def test_changing_gamma_changes_overall_score_order() -> None:
    r_pure, r_mixed = _review(1), _review(2)
    aff = {
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
    common = {
        "affinity_by_review_id": aff,
        "memberships": {},
        "selected_comms": {"c1"},
        "weights_raw": {"c1": 1.0},
        "apply_serendipity": False,
    }
    low_gamma = preference_ranked_rows(
        [r_pure, r_mixed],
        filter_settings={
            "overall_weight_alpha": 0.5,
            "overall_weight_beta": 0.0,
            "overall_weight_gamma": 0.0,
        },
        **common,
    )
    high_gamma = preference_ranked_rows(
        [r_pure, r_mixed],
        filter_settings={
            "overall_weight_alpha": 0.0,
            "overall_weight_beta": 0.0,
            "overall_weight_gamma": 1.0,
        },
        **common,
    )
    assert [row["review_id"] for row in low_gamma] == [1, 2]
    assert [row["review_id"] for row in high_gamma] == [2, 1]


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
        assert "style_breadth_norm" in row
        assert "breadth_norm" in row
        assert "album_style_breadth" in row
        assert "alpha" in row and "beta" in row and "gamma" in row


def test_serendipity_zero_preserves_score_order() -> None:
    r_a, r_b = _review(100), _review(200)
    incoming = [r_a, r_b]
    aff = {
        100: {
            "communities": {
                "res_10": [{"id": "c1", "score": 1.0}],
            },
        },
        200: {
            "communities": {
                "res_10": [
                    {"id": "c1", "score": 0.5},
                    {"id": "c9", "score": 0.5},
                ],
            },
        },
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
