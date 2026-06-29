"""Filter normalization and session-state accessors for the taste wizard."""

from __future__ import annotations

from typing import Any

import streamlit as st

# Voreinstellung Rating-Filter (Finetuning / fehlende filter_settings).
DEFAULT_PLATTENTESTS_RATING_FILTER_MIN = 7
DEFAULT_PLATTENTESTS_RATING_FILTER_MAX = 10

# Session-State-Schlüssel für das Plattenlabel-Multiselect auf der Filterseite.
FILTER_PLATTENLABEL_MULTISELECT_KEY = "filter_plattenlabel_multiselect"

# After Schritt 3 (Filter): optional save-to-account prompt (session flags).
FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY = "filter_account_save_prompt_active"
WIZARD_ACCOUNT_SAVE_INTENT_KEY = "wizard_account_save_intent"

# Streamlit widget session keys for Schritt 3 sliders (cleared on taste reset).
FILTER_FLOW_WIDGET_KEY_YEAR_RANGE = "filter_flow_year_range"
FILTER_FLOW_WIDGET_KEY_RATING_RANGE = "filter_flow_rating_range"
FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT = "filter_flow_style_match_pct"
FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA = "filter_flow_overall_alpha"
FILTER_FLOW_WIDGET_KEY_OVERALL_BETA = "filter_flow_overall_beta"
FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA = "filter_flow_overall_gamma"

FILTER_FLOW_WIDGET_KEYS: tuple[str, ...] = (
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
    FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
)

# Checkbox/slider keys on Schritt 1/2/3 that must be dropped when taste resets.
TASTE_WIZARD_WIDGET_KEY_PREFIXES: tuple[str, ...] = (
    "comm_sel_",
    "broad_cat_",
    "weight_comm_",
)

# Sammel-Option in der Filter-UI für seltene Plattenlabels.
PLATTENLABEL_SONSTIGE_UI = "Sonstige"

# Schrittweite für den Passungs-Slider in Prozent (entspricht 0.05 im 0-1-Score).
STYLE_MATCH_FILTER_PERCENT_STEP = 5

_FILTER_EXPANDER_VSPACE_GAPS = frozenset({"sm", "md", "lg", "xl"})


def clamp_plattentests_rating_filter_range(
    rating_min: Any,
    rating_max: Any,
) -> tuple[int, int]:
    """Coerce Plattentests rating filter bounds to whole numbers from 0 to 10.

    Legacy session values may be floats; values are rounded, clamped to the
    scale, and swapped if min exceeded max. Ungültige Eingaben fallen auf
    die übliche UI-Voreinstellung (7-10) zurück.
    """
    try:
        lo = round(float(rating_min))
    except (TypeError, ValueError):
        lo = DEFAULT_PLATTENTESTS_RATING_FILTER_MIN
    try:
        hi = round(float(rating_max))
    except (TypeError, ValueError):
        hi = DEFAULT_PLATTENTESTS_RATING_FILTER_MAX
    lo = max(0, min(10, lo))
    hi = max(0, min(10, hi))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def clamp_year_filter_bounds(
    year_min: Any,
    year_max: Any,
    *,
    year_cap: int,
    year_floor: int = 1990,
) -> tuple[int, int]:
    """Clamp stored year range to [year_floor, year_cap] and ensure min <= max."""
    try:
        lo = int(year_min)
    except (TypeError, ValueError):
        lo = year_floor
    try:
        hi = int(year_max)
    except (TypeError, ValueError):
        hi = year_cap
    lo = max(year_floor, min(lo, year_cap))
    hi = max(year_floor, min(hi, year_cap))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def expand_plattenlabel_ui_selection(
    ui: list[str],
    rare: list[str],
    *,
    sonstige_token: str = PLATTENLABEL_SONSTIGE_UI,
) -> list[str]:
    """Turn multiselect values into concrete labels (expand „Sonstige“)."""
    picked = {str(x).strip() for x in ui if str(x).strip()}
    if sonstige_token in picked:
        picked.discard(sonstige_token)
        picked.update(str(r).strip() for r in rare if str(r).strip())
    return sorted(picked)


def collapse_plattenlabel_ui_selection(
    concrete: set[str],
    frequent: list[str],
    rare: list[str],
    *,
    sonstige_token: str = PLATTENLABEL_SONSTIGE_UI,
) -> list[str]:
    """Build multiselect values from stored concrete label set."""
    rare_set = frozenset(str(r).strip() for r in rare if str(r).strip())
    ui: list[str] = [f for f in frequent if f in concrete]
    if rare_set and rare_set <= concrete:
        ui.append(sonstige_token)
    return ui


def plattenlabel_filter_passes(
    album_labels: list[str] | None,
    selection: Any,
    all_labels: list[str],
) -> bool:
    """Whether an album passes the Plattenlabel expert filter."""
    if not all_labels:
        return True
    all_set = frozenset(str(x).strip() for x in all_labels if str(x).strip())
    if selection is None:
        return True
    if not isinstance(selection, list):
        return True
    sel_set = frozenset(str(x).strip() for x in selection if str(x).strip())
    if sel_set == all_set:
        return True
    raw_album = list(album_labels) if album_labels else []
    album_set = frozenset(str(x).strip() for x in raw_album if str(x).strip())
    if not sel_set:
        return len(album_set) == 0
    if not album_set:
        return True
    return bool(album_set & sel_set)


def normalize_filter_expander_vspace_gap(gap: str) -> str:
    """Return a valid spacer size key for Finetuning expander vertical gaps."""
    return gap if gap in _FILTER_EXPANDER_VSPACE_GAPS else "md"


def get_selected_communities() -> set[str]:
    """Return the set of selected community IDs."""
    primary = st.session_state.get("selected_communities")
    if isinstance(primary, set) and primary:
        return {str(c) for c in primary}
    artist_comms = st.session_state.get("artist_flow_selected_communities") or set()
    genre_comms = st.session_state.get("genre_flow_selected_communities") or set()
    return {str(c) for c in artist_comms} | {str(c) for c in genre_comms}


__all__ = [
    "DEFAULT_PLATTENTESTS_RATING_FILTER_MAX",
    "DEFAULT_PLATTENTESTS_RATING_FILTER_MIN",
    "FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY",
    "FILTER_FLOW_WIDGET_KEYS",
    "FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA",
    "FILTER_FLOW_WIDGET_KEY_OVERALL_BETA",
    "FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA",
    "FILTER_FLOW_WIDGET_KEY_RATING_RANGE",
    "FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT",
    "FILTER_FLOW_WIDGET_KEY_YEAR_RANGE",
    "FILTER_PLATTENLABEL_MULTISELECT_KEY",
    "PLATTENLABEL_SONSTIGE_UI",
    "TASTE_WIZARD_WIDGET_KEY_PREFIXES",
    "WIZARD_ACCOUNT_SAVE_INTENT_KEY",
    "clamp_plattentests_rating_filter_range",
    "clamp_year_filter_bounds",
    "collapse_plattenlabel_ui_selection",
    "expand_plattenlabel_ui_selection",
    "get_selected_communities",
    "normalize_filter_expander_vspace_gap",
    "plattenlabel_filter_passes",
]
