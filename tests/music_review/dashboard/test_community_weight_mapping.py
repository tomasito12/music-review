"""Tests for community weight bias vs stored [0, 1] mapping."""

from __future__ import annotations

import pytest

from music_review.dashboard.community_weight_mapping import (
    community_weight_bias_from_stored,
    community_weight_stored_from_bias,
)


def test_stored_from_bias_center_is_half() -> None:
    assert community_weight_stored_from_bias(0.0) == pytest.approx(0.5)


def test_stored_from_bias_endpoints() -> None:
    assert community_weight_stored_from_bias(-1.0) == pytest.approx(0.0)
    assert community_weight_stored_from_bias(1.0) == pytest.approx(1.0)


def test_stored_from_bias_clamps_high() -> None:
    assert community_weight_stored_from_bias(5.0) == pytest.approx(1.0)


def test_stored_from_bias_clamps_low() -> None:
    assert community_weight_stored_from_bias(-9.0) == pytest.approx(0.0)


def test_bias_from_stored_round_trip() -> None:
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        b = community_weight_bias_from_stored(w)
        assert community_weight_stored_from_bias(b) == pytest.approx(w)


def test_bias_from_stored_clamps_stored() -> None:
    assert community_weight_bias_from_stored(-1.0) == pytest.approx(-1.0)
    assert community_weight_bias_from_stored(2.0) == pytest.approx(1.0)
