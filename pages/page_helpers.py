"""Shared data-loading and formatting helpers for Streamlit pages."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from music_review.config import resolve_data_path
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
