"""Shared playlist suggestion UI for newest reviews and the album archive."""

from __future__ import annotations

import logging
import random
import secrets
from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from pages.neueste_reviews_pool import preference_rank_rows_for_reviews
from pages.recommendations_pool import archive_playlist_candidates

from music_review.dashboard.playlist_builder import (
    PlaylistSuggestion,
    SelectionStrategy,
    amplify_preference_weights,
    build_album_weights,
    build_playlist_suggestions,
)
from music_review.domain.models import Review

PLAYLIST_LAST_SUGGESTIONS_KEY = "playlist_last_suggestions_v1"
PLAYLIST_LAST_NAME_KEY = "playlist_last_display_name_v1"

_TASTE_ORIENTATION_OPTIONS: tuple[str, ...] = (
    "gar nicht",
    "etwas",
    "mittel",
    "stark",
)
_TASTE_ORIENTATION_EXPONENT: dict[str, float] = {
    "gar nicht": 1.0,
    "etwas": 1.0,
    "mittel": 2.0,
    "stark": 3.0,
}

_SOURCE_KIND_LABELS: dict[str, str] = {
    "highlight": "Highlight",
    "fallback": "Albumtrack",
}

_LOGGER = logging.getLogger(__name__)


def _default_playlist_name() -> str:
    """Default playlist label for display: Plattenradar YYYY-MM-DD."""
    return f"Plattenradar {date.today().isoformat()}"


def _suggestions_to_display_rows(
    suggestions: list[PlaylistSuggestion],
) -> list[dict[str, str]]:
    """Map suggestions to German column labels for the results table."""
    rows: list[dict[str, str]] = []
    for item in suggestions:
        rows.append(
            {
                "Künstler": item.artist,
                "Album": item.album,
                "Titel": item.track_title,
                "Quelle": _SOURCE_KIND_LABELS.get(item.source_kind, item.source_kind),
            },
        )
    return rows


def _render_suggestions_table(suggestions: list[PlaylistSuggestion]) -> None:
    """Show the latest suggestion list when present."""
    if not suggestions:
        st.info("Noch keine Vorschläge. Bitte „Playlist vorschlagen“ wählen.")
        return
    rows = _suggestions_to_display_rows(suggestions)
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(f"{len(suggestions)} Titel in der Vorschlagsliste.")


def _generate_suggestions(
    *,
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
    target_count: int,
    taste_exponent: float,
    selection_strategy: SelectionStrategy,
) -> list[PlaylistSuggestion]:
    """Run the suggestion pipeline synchronously."""
    chosen_reviews, weights, raw_scores = build_album_weights(reviews, ranked_rows)
    if not chosen_reviews:
        return []
    rng = random.Random(secrets.randbits(64))
    alloc_weights = amplify_preference_weights(weights, exponent=taste_exponent)
    return build_playlist_suggestions(
        reviews=chosen_reviews,
        weights=alloc_weights,
        raw_scores=raw_scores,
        target_count=target_count,
        rng=rng,
        selection_strategy=selection_strategy,
    )


def render_playlist_section(
    *,
    reviews: list[Review],
    resolve_ranked_rows: Callable[[str], list[dict[str, Any]] | None],
    key_prefix: str,
    default_song_count: int,
    selection_strategy: SelectionStrategy,
) -> None:
    """Render controls and the suggestion table for one source tab."""
    name_key = f"{key_prefix}-playlist-name"
    target_count_key = f"{key_prefix}-song-count"
    taste_key = f"{key_prefix}-taste-orientation"
    generate_key = f"{key_prefix}-generate"

    target_count = st.slider(
        "Wie viele Songs sollen auf der Playlist stehen?",
        min_value=5,
        max_value=50,
        value=default_song_count,
        step=1,
        key=target_count_key,
    )
    taste_orientation = st.select_slider(
        "Wie stark soll sich die Playlist an deinem persönlichen Geschmack "
        "orientieren?",
        options=list(_TASTE_ORIENTATION_OPTIONS),
        value="etwas",
        key=taste_key,
    )
    if name_key not in st.session_state:
        st.session_state[name_key] = _default_playlist_name()
    playlist_name = st.text_input(
        "Name der Playlist (nur Anzeige)",
        key=name_key,
    )

    generate_clicked = st.button(
        "Playlist vorschlagen",
        type="primary",
        key=generate_key,
        width="stretch",
    )

    if generate_clicked:
        ranked_rows = resolve_ranked_rows(taste_orientation)
        taste_exponent = _TASTE_ORIENTATION_EXPONENT[taste_orientation]
        suggestions = _generate_suggestions(
            reviews=reviews,
            ranked_rows=ranked_rows,
            target_count=target_count,
            taste_exponent=taste_exponent,
            selection_strategy=selection_strategy,
        )
        if not suggestions:
            st.warning(
                "Es konnten keine Playlist-Vorschläge erzeugt werden. "
                "Bitte Pool oder Einstellungen prüfen."
            )
        else:
            st.session_state[PLAYLIST_LAST_SUGGESTIONS_KEY] = suggestions
            st.session_state[PLAYLIST_LAST_NAME_KEY] = (
                playlist_name.strip() or _default_playlist_name()
            )
            if len(suggestions) < target_count:
                st.warning(
                    f"Es wurden {len(suggestions)} von {target_count} gewünschten "
                    "Titeln gefunden (wenige eindeutige Tracks im Pool)."
                )

    stored = st.session_state.get(PLAYLIST_LAST_SUGGESTIONS_KEY)
    if isinstance(stored, list) and stored:
        display_name = st.session_state.get(PLAYLIST_LAST_NAME_KEY)
        if isinstance(display_name, str) and display_name.strip():
            st.subheader(display_name.strip())
        _render_suggestions_table(stored)


def render_neueste_playlist_section(*, reviews: list[Review]) -> None:
    """Build a suggestion list from the newest-reviews pool."""
    if not reviews:
        st.info("Keine Rezensionen verfügbar.")
        return

    def _resolve_ranked_rows(taste_orientation: str) -> list[dict[str, Any]] | None:
        if taste_orientation == "gar nicht":
            return None
        return preference_rank_rows_for_reviews(reviews)

    render_playlist_section(
        reviews=reviews,
        resolve_ranked_rows=_resolve_ranked_rows,
        key_prefix="newest",
        default_song_count=min(30, max(5, len(reviews))),
        selection_strategy="stratified",
    )


def render_archive_playlist_section() -> None:
    """Build a suggestion list from the scored album archive."""
    reviews, ranked_rows = archive_playlist_candidates()
    if not reviews or ranked_rows is None:
        st.info(
            "Keine passenden Alben gefunden. Bitte zuerst auf "
            "„Musikpräferenzen ändern“ Stilrichtungen wählen oder Filter "
            "im Filter-Schritt anpassen."
        )
        return

    def _resolve_ranked_rows(_taste_orientation: str) -> list[dict[str, Any]] | None:
        return ranked_rows

    render_playlist_section(
        reviews=reviews,
        resolve_ranked_rows=_resolve_ranked_rows,
        key_prefix="archive",
        default_song_count=min(30, max(5, len(reviews))),
        selection_strategy="weighted_sample",
    )
