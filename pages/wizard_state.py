"""Taste-wizard session reset, pruning, and step-state helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from pages._streamlit_ctx import st
from pages.filter_state import (
    DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
    FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
    FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
    FILTER_FLOW_WIDGET_KEY_SPECTRUM,
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
    FILTER_PLATTENLABEL_MULTISELECT_KEY,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
)
from pages.page_formatting import (
    snap_spectrum_crossover,
    style_match_percent_tuple_for_slider,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_OVERALL_ALPHA,
    RECOMMENDATION_OVERALL_BETA,
    RECOMMENDATION_OVERALL_GAMMA,
)
from music_review.dashboard.community_weight_mapping import (
    community_weight_bias_from_stored,
)
from music_review.dashboard.taste_setup import (
    clear_taste_wizard_reset_pending,
    data_implies_taste_setup_complete,
    is_taste_setup_complete,
    mark_taste_wizard_reset_pending,
)


def session_taste_setup_complete() -> bool:
    """True when genre, communities, and filter merge step are done for this session."""
    return is_taste_setup_complete(st.session_state)


def refresh_taste_wizard_after_filter_save() -> None:
    """Clear the post-reset gate once merged filter data satisfies completion rules."""
    if data_implies_taste_setup_complete(st.session_state):
        clear_taste_wizard_reset_pending(st.session_state)


def _seed_filter_flow_main_sliders(state: MutableMapping[str, Any]) -> None:
    """Assign Schritt-3 main filter slider keys so Streamlit shows defaults."""
    from pages import page_helpers as ph

    year_floor = ph.cached_min_release_year_from_corpus()
    year_cap = ph.cached_max_release_year_from_corpus()
    y_lo, y_hi = clamp_year_filter_bounds(
        year_floor,
        year_cap,
        year_cap=year_cap,
        year_floor=year_floor,
    )
    r_lo, r_hi = clamp_plattentests_rating_filter_range(
        DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
        DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    )
    pct_lo, pct_hi = style_match_percent_tuple_for_slider(0.0, 1.0)
    spectrum_val = snap_spectrum_crossover(RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER)
    state[FILTER_FLOW_WIDGET_KEY_YEAR_RANGE] = (y_lo, y_hi)
    state[FILTER_FLOW_WIDGET_KEY_RATING_RANGE] = (r_lo, r_hi)
    state[FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT] = (pct_lo, pct_hi)
    state[FILTER_FLOW_WIDGET_KEY_SPECTRUM] = spectrum_val
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA] = float(RECOMMENDATION_OVERALL_ALPHA)
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_BETA] = float(RECOMMENDATION_OVERALL_BETA)
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA] = float(RECOMMENDATION_OVERALL_GAMMA)


def _seed_weight_comm_sliders(state: MutableMapping[str, Any]) -> None:
    """Reset per-community weight slider keys to neutral (matches default raw)."""
    bias = community_weight_bias_from_stored(
        float(RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW),
    )
    for k in list(state.keys()):
        if isinstance(k, str) and k.startswith("weight_comm_"):
            state[k] = bias


def _pop_taste_wizard_widget_session_keys(state: MutableMapping[str, Any]) -> None:
    """Reset Streamlit widget keys so checkboxes/sliders re-sync to cleared data."""
    for k in list(state.keys()):
        if not isinstance(k, str):
            continue
        if k.startswith(("broad_cat_", "comm_sel_")):
            state[k] = False
        elif k.startswith("weight_comm_"):
            state.pop(k, None)
    _seed_filter_flow_main_sliders(state)


def _reset_filters() -> None:
    """Clear all filter/community selections back to defaults."""
    st.session_state["selected_communities"] = set()
    st.session_state["selected_broad_categories"] = set()
    st.session_state["artist_flow_selected_communities"] = set()
    st.session_state["genre_flow_selected_communities"] = set()
    st.session_state["filter_settings"] = {}
    st.session_state["community_weights_raw"] = {}
    st.session_state.pop(FILTER_PLATTENLABEL_MULTISELECT_KEY, None)
    _pop_taste_wizard_widget_session_keys(st.session_state)


def reset_taste_preferences() -> None:
    """Clear taste-related session keys; the user must run the setup wizard again."""
    _reset_filters()
    mark_taste_wizard_reset_pending(st.session_state)
    st.session_state["flow_mode"] = None


def _drop_widget_keys_for_community(state: MutableMapping[str, Any], cid: str) -> None:
    """Reset per-community Streamlit widget keys so checkbox/slider state resets."""
    state[f"comm_sel_{cid}"] = False
    state.pop(f"weight_comm_{cid}", None)


def prune_weights_to_selected_communities() -> int:
    """Drop community weights for communities that are no longer selected."""
    weights = st.session_state.get("community_weights_raw")
    if not isinstance(weights, dict) or not weights:
        return 0
    selected_raw = st.session_state.get("selected_communities")
    if isinstance(selected_raw, set):
        selected = {str(c) for c in selected_raw}
    else:
        selected = set()
    stale = [cid for cid in list(weights.keys()) if str(cid) not in selected]
    for cid in stale:
        weights.pop(cid, None)
        st.session_state.pop(f"weight_comm_{cid}", None)
    st.session_state["community_weights_raw"] = weights
    return len(stale)


def prune_communities_to_selected_broad_categories() -> int:
    """Drop selected communities whose broad categories are no longer selected."""
    selected_broad_raw = st.session_state.get("selected_broad_categories")
    if not isinstance(selected_broad_raw, set) or not selected_broad_raw:
        return 0
    selected_comms_raw = st.session_state.get("selected_communities")
    if not isinstance(selected_comms_raw, set) or not selected_comms_raw:
        return 0
    from pages import page_helpers as ph

    _broad_cats, mappings = ph.cached_load_broad_categories_res_10()
    if not mappings:
        return 0
    selected_broad: set[str] = {str(c) for c in selected_broad_raw}
    keep: set[str] = set()
    removed: list[str] = []
    for cid_raw in selected_comms_raw:
        cid = str(cid_raw)
        cats = mappings.get(cid) or ["Sonstige"]
        if set(cats) & selected_broad:
            keep.add(cid)
        else:
            removed.append(cid)
    if not removed:
        return 0
    st.session_state["selected_communities"] = keep
    for cid in removed:
        _drop_widget_keys_for_community(st.session_state, cid)
    prune_weights_to_selected_communities()
    return len(removed)


def _reset_step3_filter_and_weights() -> None:
    """Shared cleanup for Schritt 3: filter settings and per-style weights."""
    st.session_state["filter_settings"] = {}
    st.session_state["community_weights_raw"] = {}
    st.session_state.pop(FILTER_PLATTENLABEL_MULTISELECT_KEY, None)
    _seed_filter_flow_main_sliders(st.session_state)
    _seed_weight_comm_sliders(st.session_state)


def reset_step1_cascade() -> None:
    """Cascade reset starting at Schritt 1 (clears all three steps)."""
    reset_taste_preferences()


def reset_step2_cascade() -> None:
    """Cascade reset starting at Schritt 2: clears fine styles and per-style weights."""
    st.session_state["selected_communities"] = set()
    st.session_state["artist_flow_selected_communities"] = set()
    st.session_state["genre_flow_selected_communities"] = set()
    st.session_state["community_weights_raw"] = {}
    for key in list(st.session_state.keys()):
        if not isinstance(key, str):
            continue
        if key.startswith("comm_sel_"):
            st.session_state[key] = False
        elif key.startswith("weight_comm_"):
            st.session_state.pop(key, None)
    mark_taste_wizard_reset_pending(st.session_state)


def reset_step3() -> None:
    """Reset only Schritt 3 (filter + weighting); leaves Schritt 1 and 2 intact."""
    _reset_step3_filter_and_weights()
    mark_taste_wizard_reset_pending(st.session_state)


def has_step1_state() -> bool:
    """True when Schritt 1 holds any broad-category selection."""
    raw = st.session_state.get("selected_broad_categories")
    return bool(isinstance(raw, set) and raw)


def has_step2_state() -> bool:
    """True when Schritt 2 holds any fine-style (community) selection."""
    raw = st.session_state.get("selected_communities")
    if isinstance(raw, set) and raw:
        return True
    artist = st.session_state.get("artist_flow_selected_communities")
    genre = st.session_state.get("genre_flow_selected_communities")
    if isinstance(artist, set) and artist:
        return True
    return bool(isinstance(genre, set) and genre)


def has_step3_state() -> bool:
    """True when Schritt 3 holds filter settings or per-style weights."""
    fs = st.session_state.get("filter_settings")
    if isinstance(fs, dict) and fs:
        return True
    weights = st.session_state.get("community_weights_raw")
    return bool(isinstance(weights, dict) and weights)
