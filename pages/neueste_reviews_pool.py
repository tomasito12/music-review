"""Shared newest-reviews pool for Neueste Rezensionen and Spotify playlist UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
from pages.page_helpers import get_selected_communities, load_community_memberships

from music_review.config import resolve_data_path
from music_review.dashboard.preference_ranking import (
    global_breadth_norm_by_review_id,
    preference_ranked_rows,
)
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

RECENT_DEFAULT = 20
RES_KEY = "res_10"


def ensure_neueste_session_defaults() -> None:
    """Defaults for profile bar and preference ranking (same as Filter Flow)."""
    if "filter_settings" not in st.session_state:
        st.session_state["filter_settings"] = {}
    if "community_weights_raw" not in st.session_state:
        st.session_state["community_weights_raw"] = {}


@st.cache_data(ttl=300)
def _load_newest_reviews(n: int) -> list[Review]:
    path = resolve_data_path("data/reviews.jsonl")
    if not path.is_file():
        return []
    reviews = load_reviews_from_jsonl(path)
    reviews.sort(key=lambda r: int(r.id), reverse=True)
    return reviews[: max(1, n)]


@st.cache_data(ttl=300)
def _load_all_reviews_for_breadth_norm() -> list[Review]:
    """Full corpus for global coverage percentile (breadth_norm)."""
    path = resolve_data_path("data/reviews.jsonl")
    if not path.is_file():
        return []
    return load_reviews_from_jsonl(path)


@st.cache_data(ttl=300)
def _cached_global_breadth_norm_map(
    selected_key: tuple[str, ...],
    weights_key: tuple[tuple[str, float], ...],
) -> dict[int, float]:
    all_rev = _load_all_reviews_for_breadth_norm()
    if not all_rev:
        return {}
    memberships = load_community_memberships()
    weights = {k: float(v) for k, v in weights_key}
    return global_breadth_norm_by_review_id(
        all_rev,
        memberships=memberships,
        selected_comms=set(selected_key),
        weights_raw=weights,
    )


@st.cache_data(ttl=3600)
def _load_affinity_by_review_id() -> dict[int, dict[str, Any]]:
    path = Path(resolve_data_path("data/album_community_affinities.jsonl"))
    if not path.is_file():
        return {}
    out: dict[int, dict[str, Any]] = {}
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        rid = obj.get("review_id")
        if isinstance(rid, int):
            out[rid] = obj
    return out


def fetch_newest_reviews_pool(
    n_show: int,
) -> tuple[list[Review], list[dict[str, Any]] | None]:
    """Newest reviews and optional preference-ranked rows."""
    ensure_neueste_session_defaults()
    reviews = _load_newest_reviews(n_show)
    selected_comms = get_selected_communities()
    ranked_rows: list[dict[str, Any]] | None = None
    if selected_comms:
        filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
        weights_raw: dict[str, float] = (
            st.session_state.get("community_weights_raw") or {}
        )
        aff_map_full = _load_affinity_by_review_id()
        memberships = load_community_memberships()
        weights_key = tuple((str(k), float(v)) for k, v in sorted(weights_raw.items()))
        breadth_norm_global = _cached_global_breadth_norm_map(
            tuple(sorted(selected_comms)),
            weights_key,
        )
        ranked_rows = preference_ranked_rows(
            reviews,
            affinity_by_review_id=aff_map_full,
            memberships=memberships,
            selected_comms=selected_comms,
            weights_raw=weights_raw,
            filter_settings=filter_settings,
            apply_serendipity=False,
            global_breadth_norm_by_review_id=breadth_norm_global or None,
        )
    return reviews, ranked_rows
