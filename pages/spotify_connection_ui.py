"""Reusable Spotify connection UI: setup guide, credentials, status, login link.

These pieces are shared between the Streaming-Verbindungen page (where users
configure their Spotify app and start the OAuth flow) and the Spotify-Playlists
page (which keeps the OAuth callback URL stable and falls back to a CTA when no
connection exists yet).
"""

from __future__ import annotations

import html
from os import getenv

import streamlit as st
from pages.page_helpers import (
    SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    persist_spotify_oauth_return_page_cookie,
)
from pages.spotify_oauth_kickoff import render_spotify_login_link_under_preview
from pages.spotify_token_persist import (
    SPOTIFY_TOKEN_SESSION_KEY,
    clear_persisted_spotify_token_for_active_user,
    read_spotify_token_from_session,
)

from music_review.dashboard.user_db import (
    clear_spotify_credentials,
    load_spotify_credentials,
    save_spotify_credentials,
)
from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.spotify_client import (
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyConfigError,
)


def active_user_slug() -> str | None:
    """Return the logged-in profile slug, or None for guests."""
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return normalize_profile_slug(raw)
    except ValueError:
        return None


def try_load_user_spotify_config() -> SpotifyAuthConfig | None:
    """Load Spotify config from the logged-in user's DB credentials."""
    slug = active_user_slug()
    if slug is None:
        return None
    conn = get_db_connection()
    creds = load_spotify_credentials(conn, slug)
    if creds is None:
        return None
    client_id, client_secret = creds
    try:
        return SpotifyAuthConfig.from_user_credentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    except SpotifyConfigError:
        return None


def user_has_spotify_credentials() -> bool:
    """True when the logged-in user has stored Spotify credentials."""
    return try_load_user_spotify_config() is not None


def _section_label(text: str) -> None:
    st.markdown(
        f'<p class="rec-sort-section-label">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def render_login_required_callout() -> None:
    """Tell guests to sign in before storing Spotify credentials."""
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Bitte zuerst anmelden oder ein Konto anlegen, um die Verbindung zu Spotify "
        "in deinem Profil zu speichern."
        "</div>",
        unsafe_allow_html=True,
    )


def render_spotify_setup_guide() -> None:
    """In-app guide explaining why and how to set up a Spotify Developer App."""
    redirect_uri = (getenv("SPOTIFY_REDIRECT_URI") or "").strip()
    if not redirect_uri:
        redirect_uri = "http://127.0.0.1:8501/spotify_playlists"

    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Spotify beschränkt den Zugriff auf seine API stark: "
        "Nur Premium-Nutzer können sie verwenden, und jede App im "
        "Development-Modus ist auf wenige Nutzer begrenzt. "
        "Damit hier jeder seine eigenen Playlists erstellen kann, "
        "brauchst du eine eigene kleine Spotify-App. "
        "Das dauert nur wenige Minuten und ist kostenlos."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Profil-Anmeldung und Spotify-Redirect: Bitte dieselbe Host-Form nutzen "
        "(z. B. durchgehend <code>127.0.0.1</code> statt <code>localhost</code>), "
        "sonst erkennt der Browser nach dem Spotify-Login die Sitzung nicht."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Anleitung: Spotify-App einrichten", expanded=True):
        st.markdown(
            "1. Öffne das "
            "[Spotify Developer Dashboard]"
            "(https://developer.spotify.com/dashboard) "
            "und melde dich mit deinem Spotify-Konto an.\n"
            '2. Klicke auf **"Create App"**.\n'
            "3. Vergib einen beliebigen Namen "
            '(z. B. "Plattenradar") und eine kurze Beschreibung.\n'
            f"4. Trage als **Redirect URI** exakt ein: "
            f"`{redirect_uri}`\n"
            '5. Wähle **"Web API"** als API aus.\n'
            '6. Bestätige mit **"Save"**.\n'
            "7. Auf der App-Seite findest du unter **Settings** "
            "die **Client ID** und das **Client Secret** "
            "(bei Secret auf *View client secret* klicken). "
            "Kopiere beide Werte und trage sie unten ein."
        )

    _section_label("Spotify-Zugangsdaten hinterlegen")
    col_id, col_secret = st.columns(2)
    with col_id:
        new_client_id = st.text_input(
            "Client ID",
            key="spotify_setup_client_id",
            placeholder="32-stellige ID",
        )
    with col_secret:
        new_client_secret = st.text_input(
            "Client Secret",
            type="password",
            key="spotify_setup_client_secret",
        )
    if st.button("Zugangsdaten speichern", key="spotify_setup_save"):
        slug = active_user_slug()
        if slug is None:
            st.error(
                "Bitte zuerst ein Profil anlegen und anmelden, "
                "um Spotify-Zugangsdaten zu speichern."
            )
        elif not new_client_id or not new_client_id.strip():
            st.error("Client ID darf nicht leer sein.")
        elif not new_client_secret or not new_client_secret.strip():
            st.error("Client Secret darf nicht leer sein.")
        else:
            conn = get_db_connection()
            save_spotify_credentials(
                conn,
                slug,
                new_client_id.strip(),
                new_client_secret.strip(),
            )
            st.success("Zugangsdaten gespeichert.")
            st.rerun()


def render_spotify_credentials_management() -> None:
    """Show stored Spotify credential status and allow removal (logged-in users)."""
    slug = active_user_slug()
    if slug is None:
        return
    conn = get_db_connection()
    creds = load_spotify_credentials(conn, slug)
    if creds is None:
        return
    client_id, _ = creds
    masked_id = (
        client_id[:6] + "..." + client_id[-4:] if len(client_id) > 10 else client_id
    )
    with st.expander("Spotify-App verwalten"):
        st.caption(f"Aktuelle Client ID: `{masked_id}`")
        if st.button(
            "Zugangsdaten entfernen",
            key="spotify_creds_remove",
        ):
            clear_spotify_credentials(conn, slug)
            st.session_state.pop(SPOTIFY_TOKEN_SESSION_KEY, None)
            st.rerun()


def render_spotify_connected_status_and_disconnect() -> None:
    """Show the current Spotify connection status and a disconnect button."""
    token = read_spotify_token_from_session()
    if token is None:
        return
    st.markdown(
        '<div class="rec-callout rec-callout-info">Verbunden mit Spotify.</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        "Spotify-Verbindung trennen",
        key="spotify_connection_disconnect",
    ):
        clear_persisted_spotify_token_for_active_user()
        st.rerun()


def render_spotify_login_link_for_streaming_connections(
    client: SpotifyClient,
    *,
    link_label: str = "Mit Spotify verbinden",
) -> None:
    """Render the Spotify authorize link and remember the calling page for return.

    Sets a short-lived browser cookie so the OAuth callback (which arrives at the
    Spotify-Playlists URL) can ``switch_page`` back to the Streaming-Verbindungen
    page once the token has been stored.
    """
    persist_spotify_oauth_return_page_cookie(
        SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    )
    render_spotify_login_link_under_preview(client, link_label=link_label)
