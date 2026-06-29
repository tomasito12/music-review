"""Tests for taste widget sync after profile save/load."""

from __future__ import annotations

from pages.filter_state import (
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
)
from pages.taste_widget_sync import (
    SCORE_LAB_WIDGET_PREFIX,
    merge_filter_widgets_into_session,
    sync_filter_flow_widgets_from_settings,
    sync_score_lab_widgets_from_session,
    sync_taste_widgets_from_session,
)


def test_merge_filter_flow_widgets_overrides_stale_filter_settings() -> None:
    state: dict[str, object] = {
        "filter_settings": {"score_min": 0.7, "score_max": 1.0},
        FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT: (20, 100),
    }
    merge_filter_widgets_into_session(state)
    fs = state["filter_settings"]
    assert isinstance(fs, dict)
    assert fs["score_min"] == 0.2
    assert fs["score_max"] == 1.0


def test_merge_score_lab_widgets_into_filter_settings() -> None:
    state: dict[str, object] = {
        "filter_settings": {"score_min": 0.7, "score_max": 1.0},
        f"{SCORE_LAB_WIDGET_PREFIX}score_min": 0.2,
        f"{SCORE_LAB_WIDGET_PREFIX}score_max": 0.95,
    }
    merge_filter_widgets_into_session(state)
    fs = state["filter_settings"]
    assert isinstance(fs, dict)
    assert fs["score_min"] == 0.2
    assert fs["score_max"] == 0.95


def test_merge_score_lab_overrides_filter_flow_percent_slider() -> None:
    state: dict[str, object] = {
        "filter_settings": {"score_min": 0.7, "score_max": 1.0},
        FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT: (70, 100),
        f"{SCORE_LAB_WIDGET_PREFIX}score_min": 0.2,
    }
    merge_filter_widgets_into_session(state)
    fs = state["filter_settings"]
    assert isinstance(fs, dict)
    assert fs["score_min"] == 0.2


def test_merge_filter_flow_year_range_into_filter_settings() -> None:
    state: dict[str, object] = {
        "filter_settings": {"year_min": 1990, "year_max": 2020},
        FILTER_FLOW_WIDGET_KEY_YEAR_RANGE: (2005, 2015),
    }
    merge_filter_widgets_into_session(state)
    fs = state["filter_settings"]
    assert isinstance(fs, dict)
    assert fs["year_min"] == 2005
    assert fs["year_max"] == 2015


def test_sync_filter_flow_widgets_maps_score_min_to_percent_slider() -> None:
    state: dict[str, object] = {
        FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT: (70, 100),
    }
    sync_filter_flow_widgets_from_settings(
        state,
        {"score_min": 0.2, "score_max": 1.0},
    )
    assert state[FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT] == (20, 100)


def test_sync_score_lab_widgets_uses_filter_settings() -> None:
    state: dict[str, object] = {
        "selected_communities": {"C001"},
        "filter_settings": {
            "score_min": 0.2,
            "score_max": 1.0,
            "overall_weight_alpha": 0.5,
            "overall_weight_beta": 0.25,
            "overall_weight_gamma": 0.25,
            "community_spectrum_crossover": 0.5,
        },
        "community_weights_raw": {"C001": 1.0},
        f"{SCORE_LAB_WIDGET_PREFIX}score_min": 0.7,
    }
    sync_score_lab_widgets_from_session(state)
    assert state[f"{SCORE_LAB_WIDGET_PREFIX}score_min"] == 0.2


def test_sync_taste_widgets_updates_community_checkboxes() -> None:
    state: dict[str, object] = {
        "selected_communities": {"C001"},
        "comm_sel_C001": False,
        "comm_sel_C999": True,
        "filter_settings": {"score_min": 0.0, "score_max": 1.0},
    }
    sync_taste_widgets_from_session(state)
    assert state["comm_sel_C001"] is True
    assert state["comm_sel_C999"] is False
