"""Tests for Score Lab album score walkthrough tables."""

from __future__ import annotations

import pytest
from tests.music_review.dashboard.test_score_lab import _affinity, _inputs, _profile

from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.application.recommendation_service import RecommendationInputs
from music_review.dashboard.score_lab import build_score_lab_rows
from music_review.dashboard.score_lab_walkthrough import build_album_score_walkthrough
from music_review.domain.models import Review


def _review_with_refs(review_id: int) -> Review:
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist="Artist",
        album=f"Album {review_id}",
        text="text",
        rating=8.0,
        release_year=2020,
        references=["ref artist a", "ref artist b"],
    )


def test_walkthrough_recomputes_s_a_from_community_table() -> None:
    profile = _profile()
    inputs = _inputs()
    rows = build_score_lab_rows(profile, inputs, limit=5)
    walkthrough = build_album_score_walkthrough(
        rows[0],
        profile,
        inputs,
        batch_rows=rows,
    )
    community_sum = sum(
        float(row["weighted_contribution"]) for row in walkthrough["community_rows"]
    )
    assert community_sum == pytest.approx(float(walkthrough["summary"]["s_a"]))
    assert walkthrough["overall_steps"][-1]["step"] == "Gesamt overall_score"


def test_walkthrough_overall_terms_match_row_overall_score() -> None:
    profile = _profile()
    inputs = _inputs()
    rows = build_score_lab_rows(profile, inputs, limit=3)
    row = rows[0]
    walkthrough = build_album_score_walkthrough(
        row,
        profile,
        inputs,
        batch_rows=rows,
    )
    assert float(walkthrough["summary"]["overall_score"]) == pytest.approx(
        float(row["overall_score"]),
    )


def test_walkthrough_requires_review_in_corpus() -> None:
    profile = _profile()
    inputs = _inputs()
    with pytest.raises(ValueError, match="not found"):
        build_album_score_walkthrough(
            {"review_id": 99999, "artist": "X", "album": "Y"},
            profile,
            inputs,
            batch_rows=[],
        )


def test_walkthrough_purity_detail_matches_formula() -> None:
    profile = _profile()
    inputs = _inputs()
    rows = build_score_lab_rows(profile, inputs, limit=5)
    walkthrough = build_album_score_walkthrough(
        rows[0],
        profile,
        inputs,
        batch_rows=rows,
    )
    purity = walkthrough["purity_detail"]
    s_a = float(walkthrough["summary"]["s_a"])
    if s_a > 0:
        assert float(purity["purity_raw"]) == pytest.approx(
            float(purity["max_weighted_contribution"]) / s_a,
        )
    assert len(purity["calculation_rows"]) >= 1
    assert purity["interpretation"]


def test_walkthrough_marks_dominant_community() -> None:
    profile = _profile()
    inputs = _inputs()
    rows = build_score_lab_rows(profile, inputs, limit=3)
    walkthrough = build_album_score_walkthrough(
        rows[0],
        profile,
        inputs,
        batch_rows=rows,
    )
    dominant_rows = [
        row for row in walkthrough["community_rows"] if row.get("is_dominant")
    ]
    assert len(dominant_rows) == 1
    assert (
        dominant_rows[0]["community_id"]
        == walkthrough["purity_detail"]["dominant_community_id"]
    )


def test_walkthrough_purity_norm_detail_matches_batch_formula() -> None:
    profile = _profile()
    inputs = _inputs()
    rows = build_score_lab_rows(profile, inputs, limit=5)
    walkthrough = build_album_score_walkthrough(
        rows[0],
        profile,
        inputs,
        batch_rows=rows,
    )
    detail = walkthrough["purity_norm_detail"]
    purity_lo = float(detail["purity_lo"])
    purity_hi = float(detail["purity_hi"])
    purity_raw = float(detail["purity_raw"])
    purity_norm = float(detail["purity_norm"])
    if purity_hi > purity_lo:
        expected = (purity_raw - purity_lo) / (purity_hi - purity_lo)
        assert purity_norm == pytest.approx(expected)
    assert len(detail["batch_purity_rows"]) == len(rows)
    current_rows = [
        row for row in detail["batch_purity_rows"] if row.get("is_current_album")
    ]
    assert len(current_rows) == 1
    assert float(current_rows[0]["purity_norm"]) == pytest.approx(purity_norm)
    assert detail["interpretation"]


def test_walkthrough_includes_breadth_reference_rows() -> None:
    profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
        filter_settings=TasteFilterSettings(score_min=0.0, rating_min=0),
    )
    review = _review_with_refs(42)
    base_inputs = _inputs()
    inputs = RecommendationInputs(
        reviews=[review],
        metadata=base_inputs.metadata,
        affinities=[_affinity(42, ("C001", 0.6))],
        memberships={"ref artist a": {"res_10": "C001"}},
        communities=base_inputs.communities,
        genre_labels=base_inputs.genre_labels,
        plattenlabels=base_inputs.plattenlabels,
        year_floor=base_inputs.year_floor,
        year_cap=base_inputs.year_cap,
    )
    rows = build_score_lab_rows(profile, inputs, limit=None)
    walkthrough = build_album_score_walkthrough(
        rows[0],
        profile,
        inputs,
        batch_rows=rows,
    )
    assert len(walkthrough["breadth_rows"]) == 1
    assert walkthrough["breadth_rows"][0]["reference_mass"] > 0
