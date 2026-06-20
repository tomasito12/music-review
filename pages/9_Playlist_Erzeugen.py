"""Playlist suggestion hub: newest reviews or full archive."""

from __future__ import annotations

import streamlit as st
from pages.neueste_reviews_pool import (
    RECENT_DEFAULT,
    ensure_neueste_session_defaults,
    load_newest_reviews_slice,
)
from pages.page_helpers import (
    inject_recommendation_flow_shell_css,
    render_toolbar,
)
from pages.playlist_section import (
    render_archive_playlist_section,
    render_neueste_playlist_section,
)


def _hub_page_shell_css() -> None:
    inject_recommendation_flow_shell_css()


def _section_divider() -> None:
    st.markdown(
        '<div class="rec-results-divider" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _render_pool_count_slider() -> int:
    return st.slider(
        "Wie viele der letzten Rezensionen sollen bei der Erstellung deiner "
        "Playlist berücksichtigt werden?",
        min_value=5,
        max_value=50,
        value=RECENT_DEFAULT,
        step=1,
        key="playlist-page-pool-count",
    )


def _render_no_reviews_callout() -> None:
    st.markdown(
        '<div class="rec-callout rec-callout-warn">'
        "Keine Reviews gefunden. Pfad prüfen: <code>data/reviews.jsonl</code> "
        "(ggf. Scraping ausführen).</div>",
        unsafe_allow_html=True,
    )


def _render_newest_tab() -> None:
    n_pool = _render_pool_count_slider()
    reviews = load_newest_reviews_slice(n_pool)
    if not reviews:
        _render_no_reviews_callout()
        return
    render_neueste_playlist_section(reviews=reviews)


def _render_archive_tab() -> None:
    render_archive_playlist_section()


def main() -> None:
    """Render the playlist suggestion hub."""
    _hub_page_shell_css()
    render_toolbar("playlist_erzeugen")

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Playlist erzeugen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Erstelle eine Vorschlagsliste aus den '
        "neuesten Rezensionen oder dem gesamten Archiv, passend zu deinem "
        "Musikgeschmack.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    _section_divider()
    ensure_neueste_session_defaults()
    tab_newest, tab_archive = st.tabs(["Neueste Rezensionen", "Gesamtes Archiv"])
    with tab_newest:
        _render_newest_tab()
    with tab_archive:
        _render_archive_tab()


if __name__ == "__main__":
    main()
