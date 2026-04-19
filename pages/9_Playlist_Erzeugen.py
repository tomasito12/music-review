"""Unified playlist-creation hub for Spotify and Deezer.

Single entry point with a provider switch (Spotify / Deezer) at the top and
two source tabs underneath (Neueste Rezensionen / Gesamtes Archiv). The actual
provider-specific UI is delegated to the dedicated section modules:

* :mod:`pages.neueste_spotify_playlist_section`
* :mod:`pages.neueste_deezer_playlist_section`

OAuth callbacks are not handled here. They land on the dedicated callback
pages (``pages/9_Spotify_Playlists.py`` and ``pages/10_Deezer_Callback.py``),
which exchange the authorization code and then ``switch_page`` back to this
hub via the OAuth-return cookie.
"""

from __future__ import annotations

import streamlit as st
from pages.neueste_deezer_playlist_section import (
    render_archive_deezer_playlist_section,
    render_neueste_deezer_playlist_section,
)
from pages.neueste_reviews_pool import (
    RECENT_DEFAULT,
    configure_spotify_playlist_logging_from_env,
    ensure_neueste_session_defaults,
    load_newest_reviews_slice,
)
from pages.neueste_spotify_playlist_section import (
    render_archive_spotify_playlist_section,
    render_neueste_spotify_playlist_section,
)
from pages.page_helpers import (
    inject_recommendation_flow_shell_css,
    render_toolbar,
)

PLAYLIST_HUB_PROVIDER_SESSION_KEY = "playlist_hub_active_provider"
_PROVIDER_SPOTIFY = "Spotify"
_PROVIDER_DEEZER = "Deezer"
_PROVIDER_OPTIONS: tuple[str, ...] = (_PROVIDER_SPOTIFY, _PROVIDER_DEEZER)


def _hub_page_shell_css() -> None:
    """Shared typography and hero styles (same shell as Empfehlungen / Neueste)."""
    inject_recommendation_flow_shell_css()


def _section_divider() -> None:
    st.markdown(
        '<div class="rec-results-divider" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _resolve_active_provider() -> str:
    """Return the currently selected streaming provider label.

    Defaults to Spotify on first visit and persists the user choice in session
    state so that switching tabs / pages keeps the same provider visible.
    """
    raw = st.session_state.get(PLAYLIST_HUB_PROVIDER_SESSION_KEY)
    if isinstance(raw, str) and raw in _PROVIDER_OPTIONS:
        return raw
    st.session_state[PLAYLIST_HUB_PROVIDER_SESSION_KEY] = _PROVIDER_SPOTIFY
    return _PROVIDER_SPOTIFY


def _render_provider_selector() -> str:
    """Render the Spotify/Deezer provider radio and return the chosen value."""
    current = _resolve_active_provider()
    chosen = st.radio(
        "Streaming-Anbieter",
        options=list(_PROVIDER_OPTIONS),
        index=_PROVIDER_OPTIONS.index(current),
        horizontal=True,
        key="playlist_hub_provider_radio",
    )
    if chosen != current:
        st.session_state[PLAYLIST_HUB_PROVIDER_SESSION_KEY] = chosen
    return chosen


def _render_pool_count_slider(provider: str) -> int:
    """Render the per-provider 'how many newest reviews' slider."""
    key = (
        "spotify-page-pool-count"
        if provider == _PROVIDER_SPOTIFY
        else "deezer-page-pool-count"
    )
    return st.slider(
        "Wie viele der letzten Rezensionen sollen bei der Erstellung deiner "
        "Playlist berücksichtigt werden?",
        min_value=5,
        max_value=50,
        value=RECENT_DEFAULT,
        step=1,
        key=key,
    )


def _render_no_reviews_callout() -> None:
    """German-language callout shown when ``data/reviews.jsonl`` is empty."""
    st.markdown(
        '<div class="rec-callout rec-callout-warn">'
        "Keine Reviews gefunden. Pfad prüfen: <code>data/reviews.jsonl</code> "
        "(ggf. Scraping ausführen).</div>",
        unsafe_allow_html=True,
    )


def _render_newest_tab(provider: str) -> None:
    """Render the 'Neueste Rezensionen' tab for the chosen provider."""
    n_pool = _render_pool_count_slider(provider)
    reviews = load_newest_reviews_slice(n_pool)
    if not reviews:
        _render_no_reviews_callout()
        return
    if provider == _PROVIDER_SPOTIFY:
        render_neueste_spotify_playlist_section(reviews=reviews)
    else:
        render_neueste_deezer_playlist_section(reviews=reviews)


def _render_archive_tab(provider: str) -> None:
    """Render the 'Gesamtes Archiv' tab for the chosen provider."""
    if provider == _PROVIDER_SPOTIFY:
        render_archive_spotify_playlist_section()
    else:
        render_archive_deezer_playlist_section()


def main() -> None:
    """Render the unified playlist-creation hub."""
    configure_spotify_playlist_logging_from_env()
    _hub_page_shell_css()
    render_toolbar("playlist_erzeugen")

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Playlist erzeugen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Generiere eine Playlist - aus den '
        "neuesten Rezensionen oder dem gesamten Archiv, <br/>passend zu Deinem "
        "Musikgeschmack. Wähle deinen Streaming-Anbieter.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    provider = _render_provider_selector()
    _section_divider()

    ensure_neueste_session_defaults()
    tab_newest, tab_archive = st.tabs(["Neueste Rezensionen", "Gesamtes Archiv"])
    with tab_newest:
        _render_newest_tab(provider)
    with tab_archive:
        _render_archive_tab(provider)


if __name__ == "__main__":
    main()
