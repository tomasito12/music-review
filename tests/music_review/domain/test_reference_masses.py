"""Tests for reference-list position weights and community mass aggregation."""

from __future__ import annotations

import pytest

from music_review.domain.models import Review
from music_review.domain.reference_masses import (
    normalize_reference_artist_name,
    position_weight,
    reference_community_position_masses,
)


def test_normalize_reference_artist_name_strips_and_lowercases() -> None:
    assert normalize_reference_artist_name("  Radiohead  ") == "radiohead"
    assert normalize_reference_artist_name("") == ""


def test_position_weight_single_reference() -> None:
    assert position_weight(1, 1) == 1.0
    assert position_weight(1, 1, w_min=0.2) == 1.0


def test_position_weight_first_and_last() -> None:
    assert position_weight(1, 3, w_min=0.2) == pytest.approx(1.0)
    assert position_weight(3, 3, w_min=0.2) == 0.2
    assert position_weight(2, 3, w_min=0.2) == pytest.approx(0.6)


def test_position_weight_zero_refs_returns_w_min() -> None:
    assert position_weight(1, 0, w_min=0.2) == 0.2


def test_reference_community_position_masses_two_refs() -> None:
    review = Review(
        id=1,
        url="u",
        artist="A",
        album="B",
        text="t",
        references=["X", "Y"],
    )
    memberships = {
        "x": {"res_10": "C1"},
        "y": {"res_10": "C2"},
    }
    masses = reference_community_position_masses(
        review,
        memberships,
        res_key="res_10",
        w_min=0.2,
    )
    assert masses["C1"] == pytest.approx(1.0)
    assert masses["C2"] == pytest.approx(0.2)


def test_reference_community_position_masses_empty_refs() -> None:
    review = Review(id=1, url="u", artist="A", album="B", text="t", references=[])
    assert (
        reference_community_position_masses(
            review,
            {"x": {"res_10": "C1"}},
            res_key="res_10",
        )
        == {}
    )
