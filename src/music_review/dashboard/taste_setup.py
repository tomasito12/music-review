"""Signals for whether the taste wizard (genres + filters) is complete."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

# When True, treat taste setup as incomplete until the user finishes the filter
# step again (survives partial stray keys in session). Cleared when setup is done.
TASTE_WIZARD_RESET_PENDING_KEY = "taste_wizard_reset_pending"

# Keys always written when the Filter flow merges settings into session.
_FILTER_COMPLETION_KEYS = ("year_min", "year_max", "rating_min", "rating_max")


def communities_from_session_mapping(state: Mapping[str, Any]) -> set[str]:
    """Mirror ``get_selected_communities`` with a plain mapping (tests)."""
    primary = state.get("selected_communities")
    if isinstance(primary, set) and primary:
        return {str(c) for c in primary}
    if isinstance(primary, list) and primary:
        return {str(c) for c in primary}
    artist = state.get("artist_flow_selected_communities") or set()
    genre = state.get("genre_flow_selected_communities") or set()
    if not isinstance(artist, (set, list)):
        artist = set()
    if not isinstance(genre, (set, list)):
        genre = set()
    return {str(c) for c in artist} | {str(c) for c in genre}


def session_has_guest_taste_or_filter_prefs(state: Mapping[str, Any]) -> bool:
    """True when the session holds communities, filter settings, or style weights."""
    if communities_from_session_mapping(state):
        return True
    fs = state.get("filter_settings")
    if isinstance(fs, dict) and fs:
        return True
    cw = state.get("community_weights_raw")
    return bool(isinstance(cw, dict) and cw)


def data_implies_taste_setup_complete(state: Mapping[str, Any]) -> bool:
    """True when the user has chosen communities and completed the filter merge step."""
    fs = state.get("filter_settings")
    if not isinstance(fs, dict) or not fs:
        return False
    if not all(k in fs for k in _FILTER_COMPLETION_KEYS):
        return False
    return bool(communities_from_session_mapping(state))


def is_taste_setup_complete(state: Mapping[str, Any]) -> bool:
    """Whether onboarding taste setup is done (not blocked by a recent full reset)."""
    if state.get(TASTE_WIZARD_RESET_PENDING_KEY):
        return False
    return data_implies_taste_setup_complete(state)


def mark_taste_wizard_reset_pending(state: MutableMapping[str, Any]) -> None:
    """Call after clearing taste preferences so the user must re-run the wizard."""
    state[TASTE_WIZARD_RESET_PENDING_KEY] = True


def clear_taste_wizard_reset_pending(state: MutableMapping[str, Any]) -> None:
    """Clear after filter save or when hydrating a complete profile."""
    state.pop(TASTE_WIZARD_RESET_PENDING_KEY, None)
