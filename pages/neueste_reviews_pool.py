"""Shared newest-reviews pool for Neueste Rezensionen and Spotify playlist UI."""

from __future__ import annotations

import logging
import os
from typing import Any

import streamlit as st
from pages.page_helpers import get_selected_communities

from music_review.application.models import TasteProfile
from music_review.application.newest_reviews_service import (
    NewestReviewsInputs,
    NewestReviewsService,
)
from music_review.dashboard.cache_keys import file_cache_signature
from music_review.dashboard.data_cache import (
    cached_load_affinities_by_review_id,
    cached_load_community_memberships,
    cached_load_newest_reviews_slice,
)
from music_review.dashboard.user_profile_store import (
    profile_taste_from_account_applied_to_session,
)
from music_review.data_access.paths import (
    album_community_affinities_path,
    reviews_path,
)
from music_review.domain.models import Review

RECENT_DEFAULT = 20
RES_KEY = "res_10"

_LOGGER = logging.getLogger(__name__)

_PLAYLIST_LOG_ENV = "MUSIC_REVIEW_PLAYLIST_LOG"

_PLAYLIST_LOG_TARGET_NAMES: tuple[str, ...] = (
    "pages.neueste_reviews_pool",
    "pages.playlist_section",
    "music_review.dashboard.playlist_builder",
)

_playlist_log_configured = False


def configure_playlist_logging_from_env() -> None:
    """Attach stderr logging for playlist debug when env requests it.

    Set ``MUSIC_REVIEW_PLAYLIST_LOG`` to ``debug``, ``info``, ``1``,
    ``true``, or ``yes`` (case-insensitive) before starting Streamlit.
    """
    global _playlist_log_configured
    if _playlist_log_configured:
        return
    raw = os.environ.get(_PLAYLIST_LOG_ENV, "").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return
    level = logging.DEBUG if raw in ("debug", "1", "true", "yes") else logging.INFO
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s: %(message)s"),
    )
    for name in _PLAYLIST_LOG_TARGET_NAMES:
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.addHandler(handler)
        lg.propagate = False
    _playlist_log_configured = True


def ensure_neueste_session_defaults() -> None:
    """Defaults for profile bar and preference ranking (same as Filter Flow)."""
    if "filter_settings" not in st.session_state:
        st.session_state["filter_settings"] = {}
    if "community_weights_raw" not in st.session_state:
        st.session_state["community_weights_raw"] = {}


def load_newest_reviews_slice(n: int) -> list[Review]:
    """Return the ``n`` newest reviews by id (cached); ranking may run later."""
    return cached_load_newest_reviews_slice(max(1, n))


@st.cache_data(ttl=300)
def _cached_global_style_fit_norm_map(
    account_taste_hydrated: bool,
    selected_key: tuple[str, ...],
    weights_key: tuple[tuple[str, float], ...],
    affinities_signature: tuple[bool, int, int],
) -> dict[int, float]:
    """Corpus-wide style-fit percentile norms for the active taste profile."""
    _ = account_taste_hydrated
    aff_map = cached_load_affinities_by_review_id()
    if not aff_map or not selected_key:
        return {}
    weights_raw = dict(weights_key)
    profile = TasteProfile(
        selected_communities=selected_key,
        community_weights_raw=weights_raw,
    )
    inputs = NewestReviewsInputs(
        newest_reviews=(),
        affinity_by_review_id=aff_map,
        memberships={},
    )
    return NewestReviewsService(inputs).compute_global_style_fit_norm(profile)


@st.cache_data(ttl=300)
def _cached_global_breadth_norm_map(
    account_taste_hydrated: bool,
    selected_key: tuple[str, ...],
    weights_key: tuple[tuple[str, float], ...],
    reviews_signature: tuple[bool, int, int],
    affinities_signature: tuple[bool, int, int],
) -> dict[int, float]:
    """Corpus-wide style-breadth percentile norms for newest ranking."""
    _ = account_taste_hydrated, selected_key, weights_key
    aff_map = cached_load_affinities_by_review_id()
    if not aff_map:
        return {}
    inputs = NewestReviewsInputs(
        newest_reviews=(),
        affinity_by_review_id=aff_map,
        memberships={},
    )
    return NewestReviewsService(inputs).compute_global_breadth_norm()


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
    configure_playlist_logging_from_env()
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
    weights_key = tuple((str(k), float(v)) for k, v in sorted(weights_raw.items()))
    taste_hydrated = profile_taste_from_account_applied_to_session(st.session_state)
    reviews_sig = file_cache_signature(reviews_path())
    affinities_sig = file_cache_signature(album_community_affinities_path())
    aff_map_full = cached_load_affinities_by_review_id()
    breadth_norm_global = _cached_global_breadth_norm_map(
        taste_hydrated,
        tuple(sorted(selected_comms)),
        weights_key,
        reviews_sig,
        affinities_sig,
    )
    style_fit_norm_global = _cached_global_style_fit_norm_map(
        taste_hydrated,
        tuple(sorted(selected_comms)),
        weights_key,
        affinities_sig,
    )
    profile = TasteProfile(
        selected_communities=tuple(sorted(selected_comms)),
        community_weights_raw=weights_raw,
        filter_settings=filter_settings,
    )
    inputs = NewestReviewsInputs(
        newest_reviews=reviews,
        affinity_by_review_id=aff_map_full,
        memberships=cached_load_community_memberships(),
    )
    service = NewestReviewsService(inputs, logger=_LOGGER)
    ranked_rows = service.compute_ranked_rows(
        profile,
        apply_serendipity=False,
        global_breadth_norm=breadth_norm_global or None,
        global_style_fit_norm=style_fit_norm_global or None,
    )
    return ranked_rows


def fetch_newest_reviews_pool(
    n_show: int,
) -> tuple[list[Review], list[dict[str, Any]] | None]:
    """Newest reviews and optional preference-ranked rows."""
    configure_playlist_logging_from_env()
    ensure_neueste_session_defaults()
    reviews = load_newest_reviews_slice(n_show)
    ranked_rows = preference_rank_rows_for_reviews(reviews)
    return reviews, ranked_rows
