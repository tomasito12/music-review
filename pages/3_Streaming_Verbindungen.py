"""Streaming-Verbindungen: configure Spotify (and later Deezer) for the user."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    inject_recommendation_flow_shell_css,
    render_toolbar,
)
from pages.spotify_connection_ui import (
    active_user_slug,
    render_login_required_callout,
    render_spotify_connected_status_and_disconnect,
    render_spotify_credentials_management,
    render_spotify_login_link_for_streaming_connections,
    render_spotify_setup_guide,
    try_load_user_spotify_config,
    user_has_spotify_credentials,
)
from pages.spotify_token_persist import (
    hydrate_spotify_token_from_db_for_active_user,
    read_spotify_token_from_session,
)

from music_review.integrations.spotify_client import (
    SpotifyClient,
    resolve_spotify_redirect_uri,
)


def _spotify_browser_url_or_none() -> str | None:
    """Return the Streamlit-reported browser URL, or None if unavailable."""
    try:
        raw = st.context.url
    except Exception:
        return None
    return raw if isinstance(raw, str) else None


def _build_spotify_client_for_active_user() -> SpotifyClient | None:
    """Build a SpotifyClient from the active user's stored credentials."""
    cfg = try_load_user_spotify_config()
    if cfg is None:
        return None
    browser = _spotify_browser_url_or_none()
    effective = resolve_spotify_redirect_uri(
        configured=cfg.redirect_uri,
        browser_url=browser,
    )
    return SpotifyClient(cfg).with_redirect_uri(effective)


def _section_divider() -> None:
    st.markdown(
        '<div class="rec-results-divider" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _render_hero() -> None:
    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Streaming-Verbindungen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Verbinde dein Konto mit einem Streaming-Dienst, '
        "damit du daraus Playlists anlegen kannst.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )


def _render_spotify_subheader() -> None:
    st.markdown(
        '<h3 style="margin-top:0.5rem;margin-bottom:0.5rem;">Spotify</h3>',
        unsafe_allow_html=True,
    )


def _render_deezer_section() -> None:
    st.markdown(
        '<h3 style="margin-top:0.5rem;margin-bottom:0.5rem;">Deezer</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Deezer-Anbindung folgt in Kürze."
        "</div>",
        unsafe_allow_html=True,
    )


def _render_spotify_section_for_logged_in_user() -> None:
    """Render Spotify status, setup guide, and login link as appropriate."""
    if not user_has_spotify_credentials():
        render_spotify_setup_guide()
        return

    hydrate_spotify_token_from_db_for_active_user()
    token = read_spotify_token_from_session()
    if token is not None:
        render_spotify_connected_status_and_disconnect()
        render_spotify_credentials_management()
        return

    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Spotify-Zugangsdaten sind hinterlegt. "
        "Verbinde dich jetzt mit Spotify, um Playlists anlegen zu können."
        "</div>",
        unsafe_allow_html=True,
    )
    client = _build_spotify_client_for_active_user()
    if client is None:
        st.error(
            "Die hinterlegten Spotify-Zugangsdaten können nicht geladen werden. "
            "Bitte unter „Spotify-App verwalten“ entfernen und neu eintragen."
        )
        render_spotify_credentials_management()
        return
    render_spotify_login_link_for_streaming_connections(client)
    render_spotify_credentials_management()


def main() -> None:
    inject_recommendation_flow_shell_css()
    render_toolbar("streaming_verbindungen")
    _render_hero()

    _render_spotify_subheader()
    if active_user_slug() is None:
        render_login_required_callout()
    else:
        _render_spotify_section_for_logged_in_user()

    _section_divider()
    _render_deezer_section()


if __name__ == "__main__":
    main()
