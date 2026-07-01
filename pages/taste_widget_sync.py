"""Keep Streamlit widget keys aligned with canonical taste session fields."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

from pages.filter_state import (
    DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
    FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
    FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
)
from pages.page_formatting import (
    style_match_percent_tuple_for_slider,
    style_match_scores_from_percent_slider,
)

from music_review.config import (
    RECOMMENDATION_OVERALL_ALPHA,
    RECOMMENDATION_OVERALL_BETA,
    RECOMMENDATION_OVERALL_GAMMA,
)
from music_review.dashboard.community_weight_mapping import (
    community_weight_bias_from_stored,
)
from music_review.dashboard.data_cache import (
    cached_max_release_year_from_corpus,
    cached_min_release_year_from_corpus,
)


def _merge_filter_flow_widgets_into_settings(
    state: MutableMapping[str, Any],
    merged: dict[str, Any],
) -> None:
    """Copy Schritt-3 widget values into ``merged`` when widget keys exist."""
    year_floor = cached_min_release_year_from_corpus()
    year_cap = cached_max_release_year_from_corpus()

    year_range = state.get(FILTER_FLOW_WIDGET_KEY_YEAR_RANGE)
    if isinstance(year_range, (tuple, list)) and len(year_range) == 2:
        y_lo, y_hi = clamp_year_filter_bounds(
            year_range[0],
            year_range[1],
            year_cap=year_cap,
            year_floor=year_floor,
        )
        merged["year_min"] = y_lo
        merged["year_max"] = y_hi

    rating_range = state.get(FILTER_FLOW_WIDGET_KEY_RATING_RANGE)
    if isinstance(rating_range, (tuple, list)) and len(rating_range) == 2:
        r_lo, r_hi = clamp_plattentests_rating_filter_range(
            rating_range[0],
            rating_range[1],
        )
        merged["rating_min"] = float(r_lo)
        merged["rating_max"] = float(r_hi)

    pct_range = state.get(FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT)
    if isinstance(pct_range, (tuple, list)) and len(pct_range) == 2:
        score_min, score_max = style_match_scores_from_percent_slider(
            int(pct_range[0]),
            int(pct_range[1]),
        )
        merged["score_min"] = score_min
        merged["score_max"] = score_max

    if FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA in state:
        merged["overall_weight_alpha"] = float(
            state[FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA],
        )
    if FILTER_FLOW_WIDGET_KEY_OVERALL_BETA in state:
        merged["overall_weight_beta"] = float(
            state[FILTER_FLOW_WIDGET_KEY_OVERALL_BETA],
        )
    if FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA in state:
        merged["overall_weight_gamma"] = float(
            state[FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA],
        )


def merge_filter_widgets_into_session(state: MutableMapping[str, Any]) -> None:
    """Write live filter widget values into canonical ``filter_settings``."""
    existing = state.get("filter_settings")
    merged: dict[str, Any] = dict(existing) if isinstance(existing, dict) else {}
    _merge_filter_flow_widgets_into_settings(state, merged)
    if merged:
        state["filter_settings"] = merged


def sync_filter_flow_widgets_from_settings(
    state: MutableMapping[str, Any],
    filter_settings: Mapping[str, Any],
) -> None:
    """Update Schritt-3 filter widget keys from ``filter_settings``."""
    year_floor = cached_min_release_year_from_corpus()
    year_cap = cached_max_release_year_from_corpus()
    fs = dict(filter_settings)

    requested_year_min = fs.get("year_min")
    requested_year_max = fs.get("year_max")
    year_min = year_floor if requested_year_min is None else int(requested_year_min)
    year_max = year_cap if requested_year_max is None else int(requested_year_max)
    y_lo, y_hi = clamp_year_filter_bounds(
        year_min,
        year_max,
        year_cap=year_cap,
        year_floor=year_floor,
    )

    rating_min = float(fs.get("rating_min", DEFAULT_PLATTENTESTS_RATING_FILTER_MIN))
    rating_max = float(fs.get("rating_max", DEFAULT_PLATTENTESTS_RATING_FILTER_MAX))
    r_lo, r_hi = clamp_plattentests_rating_filter_range(rating_min, rating_max)

    pct_lo, pct_hi = style_match_percent_tuple_for_slider(
        fs.get("score_min", 0.0),
        fs.get("score_max", 1.0),
    )

    state[FILTER_FLOW_WIDGET_KEY_YEAR_RANGE] = (y_lo, y_hi)
    state[FILTER_FLOW_WIDGET_KEY_RATING_RANGE] = (int(r_lo), int(r_hi))
    state[FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT] = (pct_lo, pct_hi)
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA] = float(
        fs.get("overall_weight_alpha", RECOMMENDATION_OVERALL_ALPHA),
    )
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_BETA] = float(
        fs.get("overall_weight_beta", RECOMMENDATION_OVERALL_BETA),
    )
    state[FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA] = float(
        fs.get("overall_weight_gamma", RECOMMENDATION_OVERALL_GAMMA),
    )


def sync_community_checkbox_widgets(
    state: MutableMapping[str, Any],
    selected_communities: set[str],
) -> None:
    """Align ``comm_sel_*`` checkbox keys with ``selected_communities``."""
    selected_ids = {str(community_id) for community_id in selected_communities}
    for community_id in selected_ids:
        state[f"comm_sel_{community_id}"] = True
    for key in list(state.keys()):
        if not isinstance(key, str) or not key.startswith("comm_sel_"):
            continue
        community_id = key.removeprefix("comm_sel_")
        state[key] = community_id in selected_ids


def sync_community_weight_widgets(
    state: MutableMapping[str, Any],
    weights_raw: Mapping[str, float],
) -> None:
    """Align ``weight_comm_*`` slider keys with ``community_weights_raw``."""
    for community_id, weight in weights_raw.items():
        if not isinstance(weight, (int, float)):
            continue
        bias = community_weight_bias_from_stored(float(weight))
        state[f"weight_comm_{community_id}"] = bias


def get_selected_communities_from_state(state: Mapping[str, Any]) -> set[str]:
    """Like :func:`get_selected_communities` but for an arbitrary state mapping."""
    primary = state.get("selected_communities")
    if isinstance(primary, set) and primary:
        return {str(community_id) for community_id in primary}
    artist = state.get("artist_flow_selected_communities") or set()
    genre = state.get("genre_flow_selected_communities") or set()
    return {str(community_id) for community_id in artist} | {
        str(community_id) for community_id in genre
    }


def sync_taste_widgets_from_session(state: MutableMapping[str, Any]) -> None:
    """Sync wizard widgets from canonical session taste fields."""
    filter_settings = state.get("filter_settings")
    if isinstance(filter_settings, dict) and filter_settings:
        sync_filter_flow_widgets_from_settings(state, filter_settings)

    selected = get_selected_communities_from_state(state)
    if selected:
        sync_community_checkbox_widgets(state, selected)

    weights_raw = state.get("community_weights_raw")
    if isinstance(weights_raw, dict) and weights_raw:
        sync_community_weight_widgets(state, weights_raw)


def sync_taste_widgets_from_streamlit_session() -> None:
    """Sync widgets for the active Streamlit ``st.session_state``."""
    from pages._streamlit_ctx import st

    sync_taste_widgets_from_session(st.session_state)
