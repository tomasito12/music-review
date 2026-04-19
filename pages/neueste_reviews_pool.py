"""Shared newest-reviews pool for Neueste Rezensionen and Spotify playlist UI."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import streamlit as st
from pages.page_helpers import get_selected_communities, load_community_memberships

from music_review.config import resolve_data_path
from music_review.dashboard.preference_ranking import (
    global_breadth_norm_by_review_id,
    preference_ranked_rows,
)
from music_review.dashboard.user_profile_store import (
    profile_taste_from_account_applied_to_session,
)
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

RECENT_DEFAULT = 20
RES_KEY = "res_10"

_LOGGER = logging.getLogger(__name__)

_SPOTIFY_PLAYLIST_LOG_ENV = "MUSIC_REVIEW_SPOTIFY_PLAYLIST_LOG"

# Loggers that participate in the newest-reviews Spotify playlist flow (English logs).
_SPOTIFY_PLAYLIST_LOG_TARGET_NAMES: tuple[str, ...] = (
    "pages.neueste_reviews_pool",
    "pages.neueste_spotify_playlist_section",
    "pages.9_Spotify_Playlists",
    "music_review.dashboard.newest_spotify_playlist",
)

_spotify_playlist_log_configured = False


def configure_spotify_playlist_logging_from_env() -> None:
    """Attach stderr logging for Spotify playlist debug when env requests it.

    Set ``MUSIC_REVIEW_SPOTIFY_PLAYLIST_LOG`` to ``debug``, ``info``, ``1``,
    ``true``, or ``yes`` (case-insensitive) before starting Streamlit. Values
    ``0``, ``false``, ``no``, ``off`` disable. Idempotent for the process.
    """
    global _spotify_playlist_log_configured
    if _spotify_playlist_log_configured:
        return
    raw = os.environ.get(_SPOTIFY_PLAYLIST_LOG_ENV, "").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return
    level = logging.DEBUG if raw in ("debug", "1", "true", "yes") else logging.INFO
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s: %(message)s"),
    )
    for name in _SPOTIFY_PLAYLIST_LOG_TARGET_NAMES:
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.addHandler(handler)
        lg.propagate = False
    _spotify_playlist_log_configured = True


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


def load_newest_reviews_slice(n: int) -> list[Review]:
    """Return the ``n`` newest reviews by id (cached); ranking may run later."""
    return _load_newest_reviews(max(1, n))


@st.cache_data(ttl=300)
def _load_all_reviews_for_breadth_norm() -> list[Review]:
    """Full corpus for global coverage percentile (breadth_norm)."""
    path = resolve_data_path("data/reviews.jsonl")
    if not path.is_file():
        return []
    return load_reviews_from_jsonl(path)


@st.cache_data(ttl=300)
def _cached_global_breadth_norm_map(
    _account_taste_hydrated: bool,
    selected_key: tuple[str, ...],
    weights_key: tuple[tuple[str, float], ...],
) -> dict[int, float]:
    """Breadth norms; first arg is cache-key only (hydrated vs. session-only taste)."""
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


def preference_rank_rows_for_reviews(
    reviews: list[Review],
) -> list[dict[str, Any]] | None:
    """Preference scores for exactly ``reviews`` (same rules as the Neueste page).

    Returns ``None`` when no communities are selected (callers use uniform
    weights). Does not load reviews; only ranks the given list. Uses
    ``st.session_state`` taste keys only; when the account profile is not
    hydrated into the session (merge pending or guest session pinned), those
    keys are the temporary in-tab preferences, not a parallel DB read.
    """
    configure_spotify_playlist_logging_from_env()
    ensure_neueste_session_defaults()
    selected_comms = get_selected_communities()
    if not selected_comms:
        _LOGGER.info(
            "preference_rank_rows_for_reviews: skipped "
            "(no selected communities; uniform album weights). n_reviews=%s",
            len(reviews),
        )
        return None
    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}
    aff_map_full = _load_affinity_by_review_id()
    memberships = load_community_memberships()
    weights_key = tuple((str(k), float(v)) for k, v in sorted(weights_raw.items()))
    taste_hydrated = profile_taste_from_account_applied_to_session(st.session_state)
    breadth_norm_global = _cached_global_breadth_norm_map(
        taste_hydrated,
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
    _LOGGER.info(
        "preference_rank_rows_for_reviews: applied n_reviews=%s n_ranked_rows=%s "
        "n_selected_communities=%s",
        len(reviews),
        len(ranked_rows),
        len(selected_comms),
    )
    _LOGGER.debug(
        "preference_rank_rows_for_reviews: selected_community_ids=%s "
        "filter_settings_keys=%s n_community_weights=%s",
        sorted(selected_comms),
        sorted((st.session_state.get("filter_settings") or {}).keys()),
        len(st.session_state.get("community_weights_raw") or {}),
    )
    return ranked_rows


def fetch_newest_reviews_pool(
    n_show: int,
) -> tuple[list[Review], list[dict[str, Any]] | None]:
    """Newest reviews and optional preference-ranked rows."""
    configure_spotify_playlist_logging_from_env()
    ensure_neueste_session_defaults()
    reviews = _load_newest_reviews(n_show)
    ranked_rows = preference_rank_rows_for_reviews(reviews)
    return reviews, ranked_rows
