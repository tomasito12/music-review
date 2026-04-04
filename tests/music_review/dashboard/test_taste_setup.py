"""Tests for taste wizard completion detection (no Streamlit)."""

from __future__ import annotations

from music_review.dashboard.taste_setup import (
    TASTE_WIZARD_RESET_PENDING_KEY,
    communities_from_session_mapping,
    data_implies_taste_setup_complete,
    is_taste_setup_complete,
    mark_taste_wizard_reset_pending,
)


def test_communities_from_session_mapping_primary_set() -> None:
    state = {"selected_communities": {"a", "b"}}
    assert communities_from_session_mapping(state) == {"a", "b"}


def test_communities_from_session_mapping_legacy_union() -> None:
    state = {
        "artist_flow_selected_communities": ["1"],
        "genre_flow_selected_communities": ["2"],
    }
    assert communities_from_session_mapping(state) == {"1", "2"}


def test_data_implies_complete_requires_communities_and_filter_keys() -> None:
    base_fs = {
        "year_min": 1990,
        "year_max": 2024,
        "rating_min": 7,
        "rating_max": 10,
    }
    assert not data_implies_taste_setup_complete(
        {"selected_communities": set(), "filter_settings": base_fs},
    )
    assert not data_implies_taste_setup_complete(
        {"selected_communities": {"c1"}, "filter_settings": {}},
    )
    assert not data_implies_taste_setup_complete(
        {
            "selected_communities": {"c1"},
            "filter_settings": {"year_min": 1990},
        },
    )
    assert data_implies_taste_setup_complete(
        {"selected_communities": {"c1"}, "filter_settings": base_fs},
    )


def test_is_taste_setup_complete_respects_reset_pending() -> None:
    state: dict[str, object] = {
        "selected_communities": {"c1"},
        "filter_settings": {
            "year_min": 1990,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
    }
    assert is_taste_setup_complete(state) is True
    mark_taste_wizard_reset_pending(state)
    assert state[TASTE_WIZARD_RESET_PENDING_KEY] is True
    assert is_taste_setup_complete(state) is False


def test_reset_pending_string_key_blocks_completion() -> None:
    state: dict[str, object] = {
        "selected_communities": {"c1"},
        "filter_settings": {
            "year_min": 1990,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        TASTE_WIZARD_RESET_PENDING_KEY: True,
    }
    assert is_taste_setup_complete(state) is False
