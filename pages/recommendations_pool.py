"""Shared recommendations computation: filter+score+sort over the album corpus.

Used by:

- The Empfehlungen page (``pages/6_Recommendations_Flow.py``) to render the
  ranked album list.
- The playlist page (``pages/9_Playlist_Erzeugen.py``, archive mode) to
  build a candidate pool with the same scoring as the Empfehlungen page.

Keeps the data loaders cached (``@st.cache_data``) so repeated calls within a
Streamlit session reuse the parsed JSONL files.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st
from pages.page_helpers import get_selected_communities

from music_review.application.models import TasteProfile
from music_review.application.recommendation_service import (
    RecommendationInputs,
    RecommendationService,
)
from music_review.dashboard.data_cache import (
    cached_load_affinities_list,
    cached_load_communities_res_10,
    cached_load_community_memberships,
    cached_load_genre_labels_res_10,
    cached_load_reviews_and_metadata,
    cached_load_sorted_unique_plattenlabels,
    cached_max_release_year_from_corpus,
    cached_min_release_year_from_corpus,
)
from music_review.domain.models import Review

LOGGER = logging.getLogger(__name__)

# German user-visible sort labels stored verbatim in ``filter_settings["sort_mode"]``.
SORT_MODE_FIXED = "Feste Reihenfolge"
SORT_MODE_RANDOM = "Mit Zufall"

# Legacy values from earlier versions of the Filter Flow are auto-migrated.
SORT_MODE_MIGRATION: dict[str, str] = {
    "Deterministisch": SORT_MODE_FIXED,
    "Serendipity": SORT_MODE_RANDOM,
}


def load_reviews_and_metadata() -> tuple[list[Review], dict[int, dict[str, Any]]]:
    """Load the corpus reviews plus the (optional) imputed metadata map."""
    return cached_load_reviews_and_metadata()


def load_affinities() -> list[dict[str, Any]]:
    """Load the album-to-community affinity records used for scoring."""
    return cached_load_affinities_list()


def compute_recommendations() -> list[dict[str, Any]]:
    """Score and sort albums from the current Streamlit session taste settings.

    Reads ``selected_communities``, ``filter_settings`` and ``community_weights_raw``
    from ``st.session_state`` (no extra profile DB read). Returns one dict per
    album that passes filters; each dict contains ``review_id``, ``artist``,
    ``album``, ``score``, ``overall_score``, ``rating``, ``year``, ``url``,
    ``text``, ``top_communities`` and the score breakdown used by the UI.
    """
    selected_comms = get_selected_communities()
    if not selected_comms:
        return []
    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}
    profile = TasteProfile.from_mapping(
        {
            "selected_communities": sorted(selected_comms),
            "filter_settings": filter_settings,
            "community_weights_raw": weights_raw,
        },
    )

    reviews, metadata = load_reviews_and_metadata()
    inputs = RecommendationInputs(
        reviews=reviews,
        metadata=metadata,
        affinities=load_affinities(),
        memberships=cached_load_community_memberships(),
        communities=cached_load_communities_res_10(),
        genre_labels=cached_load_genre_labels_res_10(),
        plattenlabels=cached_load_sorted_unique_plattenlabels(),
        year_floor=cached_min_release_year_from_corpus(),
        year_cap=cached_max_release_year_from_corpus(),
    )
    return RecommendationService(inputs).compute_archive_recommendations(profile)


def archive_playlist_candidates() -> tuple[list[Review], list[dict[str, Any]] | None]:
    """Return reviews and ranked rows from :func:`compute_recommendations`.

    The shape matches what
    :func:`music_review.dashboard.playlist_builder.build_album_weights`
    expects as ``(reviews, ranked_rows)``: each row contains ``review`` (the
    :class:`Review` object) and ``overall_score`` (float). The order follows the
    Empfehlungen ranking. Returns ``([], None)`` when no candidates are found
    (no taste set, missing data, or filters too strict).
    """
    recs = compute_recommendations()
    if not recs:
        LOGGER.info("archive playlist candidates: no recommendations available")
        return [], None
    reviews_all, _metadata = load_reviews_and_metadata()
    if not reviews_all:
        LOGGER.warning(
            "archive playlist candidates: recommendations present but corpus empty",
        )
        return [], None
    review_index: dict[int, Review] = {int(r.id): r for r in reviews_all}
    reviews_in_order: list[Review] = []
    ranked_rows: list[dict[str, Any]] = []
    for rec in recs:
        rid = rec.get("review_id")
        if not isinstance(rid, int):
            continue
        review = review_index.get(rid)
        if review is None:
            continue
        score_any = rec.get("overall_score")
        score = float(score_any) if isinstance(score_any, (int, float)) else 0.0
        reviews_in_order.append(review)
        ranked_rows.append({"review": review, "overall_score": score})
    if not reviews_in_order:
        LOGGER.warning(
            "archive playlist candidates: recommendations had no resolvable Review",
        )
        return [], None
    LOGGER.info(
        "archive playlist candidates: n_reviews=%s n_ranked_rows=%s",
        len(reviews_in_order),
        len(ranked_rows),
    )
    return reviews_in_order, ranked_rows
