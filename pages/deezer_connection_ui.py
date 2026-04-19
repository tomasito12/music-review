"""Reusable Deezer connection UI: status, optional own-app credentials, login link.

The default flow uses the project-wide shared Deezer App configured in the
``.env`` file (`DEEZER_APP_ID`, `DEEZER_APP_SECRET`, `DEEZER_REDIRECT_URI`).
Power users may optionally store their own Deezer Developer App credentials in
their profile to spread API calls across additional app quotas.
"""

from __future__ import annotations

import html
from os import getenv

import streamlit as st
from pages.deezer_oauth_kickoff import render_deezer_login_link_under_preview
from pages.deezer_token_persist import (
    DEEZER_TOKEN_SESSION_KEY,
    clear_persisted_deezer_token_for_active_user,
    read_deezer_token_from_session,
)
from pages.page_helpers import (
    DEEZER_OAUTH_RETURN_PAGE_PLAYLIST_HUB,
    DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    persist_deezer_oauth_return_page_cookie,
)

from music_review.dashboard.user_db import (
    clear_deezer_credentials,
    load_deezer_credentials,
    save_deezer_credentials,
)
from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.deezer_client import (
    DeezerAuthConfig,
    DeezerClient,
    DeezerConfigError,
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


def try_load_user_deezer_config() -> DeezerAuthConfig | None:
    """Load Deezer config from the logged-in user's DB credentials, if any."""
    slug = active_user_slug()
    if slug is None:
        return None
    conn = get_db_connection()
    creds = load_deezer_credentials(conn, slug)
    if creds is None:
        return None
    app_id, app_secret = creds
    try:
        return DeezerAuthConfig.from_user_credentials(
            app_id=app_id,
            app_secret=app_secret,
        )
    except DeezerConfigError:
        return None


def try_load_shared_deezer_config() -> DeezerAuthConfig | None:
    """Load the shared project-wide Deezer config from the environment."""
    try:
        return DeezerAuthConfig.from_env()
    except DeezerConfigError:
        return None


def resolve_deezer_auth_config() -> DeezerAuthConfig | None:
    """Per-user credentials win; otherwise fall back to the shared project app."""
    user_cfg = try_load_user_deezer_config()
    if user_cfg is not None:
        return user_cfg
    return try_load_shared_deezer_config()


def user_has_deezer_credentials() -> bool:
    """True when the logged-in user has stored Deezer credentials."""
    return try_load_user_deezer_config() is not None


def _section_label(text: str) -> None:
    st.markdown(
        f'<p class="rec-sort-section-label">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


def render_login_required_callout() -> None:
    """Tell guests to sign in before storing Deezer credentials."""
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Bitte zuerst anmelden oder ein Konto anlegen, um die Verbindung zu Deezer "
        "in deinem Profil zu speichern."
        "</div>",
        unsafe_allow_html=True,
    )


def render_deezer_shared_app_callout() -> None:
    """Reassure users that no Deezer Developer App is required by default."""
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Du kannst dich direkt mit deinem Deezer-Konto verbinden — die App "
        "von Plattenradar erledigt die Anmeldung für dich. "
        "Eigene Deezer-App-Schlüssel sind optional und nur für Power-User."
        "</div>",
        unsafe_allow_html=True,
    )


def render_deezer_setup_guide() -> None:
    """Optional in-app guide for users who want to use their own Deezer App."""
    redirect_uri = (getenv("DEEZER_REDIRECT_URI") or "").strip()
    if not redirect_uri:
        redirect_uri = "http://127.0.0.1:8501/deezer_callback"

    with st.expander("Eigene Deezer-App verwenden (optional)"):
        st.markdown(
            '<div class="rec-callout rec-callout-info">'
            "Standardmäßig wird die geteilte Plattenradar-App verwendet. "
            "Wenn du deine eigene Deezer-App hinterlegen möchtest "
            "(z. B. um separate Quoten zu nutzen), folge dieser Anleitung."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "1. Öffne den "
            "[Deezer Developer-Bereich]"
            "(https://developers.deezer.com/myapps) "
            "und melde dich mit deinem Deezer-Konto an.\n"
            '2. Klicke auf **"Create a new application"**.\n'
            "3. Vergib einen Anwendungsnamen "
            '(z. B. "Plattenradar privat") und eine kurze Beschreibung.\n'
            f"4. Trage als **Redirect URL after authentication** exakt ein: "
            f"`{redirect_uri}`\n"
            "5. Speichere die App. Auf der App-Übersicht findest du die "
            "**Application ID** und das **Secret Key** -- "
            "kopiere beide Werte und trage sie unten ein."
        )

        col_id, col_secret = st.columns(2)
        with col_id:
            new_app_id = st.text_input(
                "App-ID",
                key="deezer_setup_app_id",
                placeholder="z. B. 654321",
            )
        with col_secret:
            new_app_secret = st.text_input(
                "App-Secret",
                type="password",
                key="deezer_setup_app_secret",
            )
        if st.button("Zugangsdaten speichern", key="deezer_setup_save"):
            slug = active_user_slug()
            if slug is None:
                st.error(
                    "Bitte zuerst ein Profil anlegen und anmelden, "
                    "um Deezer-Zugangsdaten zu speichern."
                )
            elif not new_app_id or not new_app_id.strip():
                st.error("App-ID darf nicht leer sein.")
            elif not new_app_secret or not new_app_secret.strip():
                st.error("App-Secret darf nicht leer sein.")
            else:
                conn = get_db_connection()
                save_deezer_credentials(
                    conn,
                    slug,
                    new_app_id.strip(),
                    new_app_secret.strip(),
                )
                st.success("Zugangsdaten gespeichert.")
                st.rerun()


def render_deezer_credentials_management() -> None:
    """Show stored Deezer credential status and allow removal (logged-in users)."""
    slug = active_user_slug()
    if slug is None:
        return
    conn = get_db_connection()
    creds = load_deezer_credentials(conn, slug)
    if creds is None:
        return
    app_id, _ = creds
    masked_id = app_id[:4] + "..." + app_id[-2:] if len(app_id) > 6 else app_id
    with st.expander("Eigene Deezer-App verwalten"):
        st.caption(f"Aktuelle App-ID: `{masked_id}`")
        if st.button(
            "Zugangsdaten entfernen",
            key="deezer_creds_remove",
        ):
            clear_deezer_credentials(conn, slug)
            st.session_state.pop(DEEZER_TOKEN_SESSION_KEY, None)
            st.rerun()


def render_deezer_connected_status_and_disconnect() -> None:
    """Show the current Deezer connection status and a disconnect button."""
    token = read_deezer_token_from_session()
    if token is None:
        return
    st.markdown(
        '<div class="rec-callout rec-callout-info">Verbunden mit Deezer.</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        "Deezer-Verbindung trennen",
        key="deezer_connection_disconnect",
    ):
        clear_persisted_deezer_token_for_active_user()
        st.rerun()


def render_deezer_login_link_for_streaming_connections(
    client: DeezerClient,
    *,
    link_label: str = "Mit Deezer verbinden",
) -> None:
    """Render the Deezer authorize link and remember the calling page for return."""
    persist_deezer_oauth_return_page_cookie(
        DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    )
    render_deezer_login_link_under_preview(client, link_label=link_label)


def render_deezer_login_link_for_playlist_hub(
    client: DeezerClient,
    *,
    link_label: str = "Verbindung mit Deezer herstellen",
) -> None:
    """Render the Deezer authorize link from the playlist hub and remember return."""
    persist_deezer_oauth_return_page_cookie(
        DEEZER_OAUTH_RETURN_PAGE_PLAYLIST_HUB,
    )
    render_deezer_login_link_under_preview(client, link_label=link_label)
