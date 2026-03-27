"""Shared data-loading and formatting helpers for Streamlit pages."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from music_review.config import resolve_data_path
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    build_profile_payload,
    default_profiles_dir,
    save_profile,
)
from music_review.pipeline.retrieval.reference_graph import load_artist_communities


@st.cache_data(ttl=3600)
def load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities with top artists."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "communities_res_10.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    comms = data.get("communities")
    if not isinstance(comms, list):
        return []
    return [c for c in comms if isinstance(c, dict) and c.get("id")]


@st.cache_data(ttl=3600)
def load_genre_labels_res_10() -> dict[str, str]:
    """Load LLM-assigned genre labels for communities (res_10)."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "community_genre_labels_res_10.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return {}
    mapping: dict[str, str] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        label = item.get("genre_label")
        if cid is None or not label:
            continue
        mapping[str(cid)] = str(label)
    return mapping


def get_selected_communities() -> set[str]:
    """Union of communities selected in Artist and Genre flows."""
    artist_comms = st.session_state.get("artist_flow_selected_communities") or set()
    genre_comms = st.session_state.get("genre_flow_selected_communities") or set()
    artist_set = {str(c) for c in artist_comms}
    genre_set = {str(c) for c in genre_comms}
    return artist_set.union(genre_set)


def format_release_date(value: Any, release_year: Any) -> str:
    """Format release date for display cards.

    Supports datetime/date objects and ISO date strings.
    """
    if value is not None:
        if hasattr(value, "strftime"):
            try:
                return value.strftime("%d.%m.%Y")
            except Exception:
                pass
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime("%d.%m.%Y")
            except ValueError:
                pass
    if release_year is not None:
        try:
            return str(int(release_year))
        except (TypeError, ValueError):
            pass
    return ""


@st.cache_data(ttl=3600)
def load_community_memberships() -> dict[str, dict[str, str]]:
    """Load artist key (normalized) -> resolution keys -> community id."""
    mp = resolve_data_path("data/community_memberships.jsonl")
    return load_artist_communities(mp)


def save_current_profile_to_disk() -> None:
    """Persist current session settings under the active profile slug."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        st.warning("Kein Profil aktiv -- bitte zuerst anmelden.")
        return
    profiles_dir = default_profiles_dir()
    artist = st.session_state.get("artist_flow_selected_communities")
    if not isinstance(artist, set):
        artist = set()
    genre = st.session_state.get("genre_flow_selected_communities")
    if not isinstance(genre, set):
        genre = set()
    fs = st.session_state.get("filter_settings")
    if not isinstance(fs, dict):
        fs = {}
    weights = st.session_state.get("community_weights_raw")
    if not isinstance(weights, dict):
        weights = {}
    payload = build_profile_payload(
        profile_slug=active,
        flow_mode=st.session_state.get("flow_mode"),
        artist_communities=artist,
        genre_communities=genre,
        filter_settings=fs,
        community_weights_raw=weights,
    )
    save_profile(profiles_dir, active, payload)
    st.success(f"Profil '{active}' gespeichert.")


def _reset_filters() -> None:
    """Clear all filter/community selections back to defaults."""
    st.session_state["artist_flow_selected_communities"] = set()
    st.session_state["genre_flow_selected_communities"] = set()
    st.session_state["filter_settings"] = {}
    st.session_state["community_weights_raw"] = {}
    st.session_state["free_text_query"] = ""


def render_toolbar(page_key: str) -> None:
    """Compact profile/action bar at the top of every flow page."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)

    if active:
        col_status, col_save, col_reset, col_out = st.columns([3, 1, 1, 1])
        with col_status:
            st.caption(f"Angemeldet als **{active}**")
        with col_save:
            if st.button(
                "Speichern",
                key=f"tb_{page_key}_save",
                use_container_width=True,
            ):
                save_current_profile_to_disk()
        with col_reset:
            if st.button(
                "Filter zurücksetzen",
                key=f"tb_{page_key}_reset",
                use_container_width=True,
            ):
                _reset_filters()
                st.rerun()
        with col_out:
            if st.button(
                "Abmelden",
                key=f"tb_{page_key}_logout",
                use_container_width=True,
            ):
                st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
                st.rerun()
    else:
        col_status, col_login = st.columns([5, 1])
        with col_status:
            st.caption("Kein Profil aktiv")
        with col_login:
            if st.button(
                "Anmelden",
                key=f"tb_{page_key}_login",
                use_container_width=True,
            ):
                st.switch_page("pages/0_Profil.py")

    st.markdown("---")
