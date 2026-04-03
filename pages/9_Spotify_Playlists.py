from __future__ import annotations

import secrets
from dataclasses import asdict
from typing import Any

import streamlit as st

from music_review.integrations.spotify_client import (
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyPlaylist,
    SpotifyToken,
)

"""Spotify playlist helper page.

Users can connect their own Spotify account, search for tracks, and create a
playlist from selected tracks. Tokens are stored only in the Streamlit
session state so the flow is suitable for multiple users on the same app.
"""


SPOTIFY_AUTH_STATE_KEY = "spotify_auth_state"
SPOTIFY_TOKEN_KEY = "spotify_token"
SPOTIFY_SEARCH_RESULTS_KEY = "spotify_search_results_tracks"
SPOTIFY_SELECTED_URIS_KEY = "spotify_selected_track_uris"
SPOTIFY_LAST_PLAYLIST_KEY = "spotify_last_playlist"


def _load_client() -> SpotifyClient | None:
    """Return a configured SpotifyClient instance or None if config is missing."""
    try:
        cfg = SpotifyAuthConfig.from_env()
    except Exception as exc:
        st.warning(
            "Spotify-Konfiguration fehlt oder ist unvollständig "
            "(Client-ID/Redirect-URL). Bitte `.env` prüfen.",
        )
        st.caption(f"Technische Details: {exc}")
        return None
    return SpotifyClient(cfg)


def _get_stored_token() -> SpotifyToken | None:
    raw = st.session_state.get(SPOTIFY_TOKEN_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        return SpotifyToken(
            access_token=str(raw["access_token"]),
            token_type=str(raw.get("token_type", "Bearer")),
            expires_at=raw["expires_at"],
            refresh_token=raw.get("refresh_token"),
            scope=raw.get("scope"),
        )
    except Exception:
        return None


def _store_token(token: SpotifyToken) -> None:
    st.session_state[SPOTIFY_TOKEN_KEY] = asdict(token)


def _query_param_single(raw: Any) -> str | None:
    """Normalize Streamlit query param value to a single string."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        return str(raw[0])
    return str(raw)


def _clear_oauth_query_params() -> None:
    """Remove OAuth callback params so reruns do not re-trigger a failed check."""
    for key in ("code", "state", "error", "error_description"):
        if key in st.query_params:
            del st.query_params[key]


def _handle_oauth_callback(client: SpotifyClient) -> None:
    """Handle OAuth callback parameters present in the page URL."""
    params = st.query_params
    code = _query_param_single(params.get("code"))
    state = _query_param_single(params.get("state"))
    if not code or not state:
        return
    expected_state = st.session_state.get(SPOTIFY_AUTH_STATE_KEY)
    if isinstance(expected_state, str) and expected_state and state != expected_state:
        _clear_oauth_query_params()
        st.error(
            "Sicherheitsüberprüfung für den Spotify-Login fehlgeschlagen. "
            "Bitte den Verbindungsaufbau erneut starten.",
        )
        return
    with st.spinner("Spotify-Verbindung wird hergestellt …"):
        try:
            token = client.exchange_code_for_token(
                code=code,
            )
        except Exception as exc:
            _clear_oauth_query_params()
            st.error(
                "Spotify-Token konnte nicht abgerufen werden. "
                "Bitte versuche es später erneut.",
            )
            st.caption(f"Technische Details: {exc}")
            return
    _store_token(token)
    st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
    _clear_oauth_query_params()
    st.success("Du bist jetzt mit Spotify verbunden.")


def _render_connection_section(client: SpotifyClient | None) -> SpotifyToken | None:
    st.subheader("Verbindung zu Spotify")
    token = _get_stored_token()
    if client is None:
        st.info(
            "Diese Seite benötigt eine gültige Spotify-Konfiguration, um "
            "Playlists zu erstellen.",
        )
        return None
    _handle_oauth_callback(client)
    token = _get_stored_token()
    if token is not None:
        col_status, col_action = st.columns([3, 1])
        with col_status:
            st.success("Mit Spotify verbunden.")
        with col_action:
            if st.button("Verbindung trennen", key="spotify_disconnect"):
                st.session_state.pop(SPOTIFY_TOKEN_KEY, None)
                st.session_state.pop(SPOTIFY_SEARCH_RESULTS_KEY, None)
                st.session_state.pop(SPOTIFY_SELECTED_URIS_KEY, None)
                st.session_state.pop(SPOTIFY_LAST_PLAYLIST_KEY, None)
                st.rerun()
        return token

    if st.button("Mit Spotify verbinden", type="primary"):
        state = secrets.token_urlsafe(32)
        st.session_state[SPOTIFY_AUTH_STATE_KEY] = state
        auth_url = client.build_authorize_url(
            state=str(state),
        )
        st.markdown(
            f"[Zum Spotify-Login wechseln]({auth_url})",
            unsafe_allow_html=False,
        )
    else:
        st.info(
            "Noch nicht mit Spotify verbunden. Klicke auf "
            "„Mit Spotify verbinden“, um den Login zu starten.",
        )
    return None


def _render_search_section(client: SpotifyClient, token: SpotifyToken | None) -> None:
    st.subheader("Tracks suchen und auswählen")
    if token is None:
        st.info(
            "Bitte verbinde zuerst deinen Spotify-Account, bevor du nach "
            "Tracks suchst.",
        )
        return
    query = st.text_input("Suche nach Titeln oder Künstlern")
    mode = st.radio(
        "Suchtyp",
        options=("Tracks", "Künstler"),
        horizontal=True,
    )
    if st.button("Suchen", key="spotify_search_button") and query.strip():
        with st.spinner("Spotify-Suche läuft …"):
            try:
                if mode == "Künstler":
                    results = client.search_artists(
                        query=query,
                        limit=20,
                        token=token,
                    )
                else:
                    results = client.search_tracks(
                        query=query,
                        limit=20,
                        token=token,
                    )
            except Exception as exc:
                st.error("Die Suche bei Spotify ist fehlgeschlagen.")
                st.caption(f"Technische Details: {exc}")
                return
        items: list[dict[str, Any]] = []
        for r in results:
            if hasattr(r, "uri"):
                if hasattr(r, "artists"):
                    artists = ", ".join(getattr(r, "artists", ()))
                else:
                    artists = ""
                items.append(
                    {
                        "id": getattr(r, "id", ""),
                        "name": getattr(r, "name", ""),
                        "uri": getattr(r, "uri", ""),
                        "artists": artists,
                        "album": getattr(r, "album_name", None),
                    },
                )
        st.session_state[SPOTIFY_SEARCH_RESULTS_KEY] = items

    raw_results = st.session_state.get(SPOTIFY_SEARCH_RESULTS_KEY) or []
    if not raw_results:
        return

    selected_uris: set[str] = set(
        st.session_state.get(SPOTIFY_SELECTED_URIS_KEY) or [],
    )
    st.markdown("**Trefferliste**")
    for row in raw_results:
        uri = str(row.get("uri") or "")
        if not uri:
            continue
        cols = st.columns([0.1, 0.5, 0.4])
        with cols[0]:
            checked = uri in selected_uris
            new_val = st.checkbox(
                "",
                value=checked,
                key=f"spotify_sel_{uri}",
            )
            if new_val:
                selected_uris.add(uri)
            elif checked and not new_val:
                selected_uris.discard(uri)
        with cols[1]:
            name = row.get("name") or ""
            artists = row.get("artists") or ""
            st.markdown(f"**{name}**")
            if artists:
                st.caption(artists)
        with cols[2]:
            album = row.get("album") or ""
            if album:
                st.caption(album)

    st.session_state[SPOTIFY_SELECTED_URIS_KEY] = sorted(selected_uris)
    st.caption(
        f"Ausgewählte Tracks: {len(st.session_state[SPOTIFY_SELECTED_URIS_KEY])}",
    )


def _render_playlist_section(client: SpotifyClient, token: SpotifyToken | None) -> None:
    st.subheader("Playlist erzeugen und speichern")
    if token is None:
        st.info(
            "Bitte stelle zuerst die Verbindung zu Spotify her und wähle "
            "mindestens einen Track aus.",
        )
        return
    selected_uris = st.session_state.get(SPOTIFY_SELECTED_URIS_KEY) or []
    playlist_name = st.text_input("Playlist-Name")
    description = st.text_area("Beschreibung (optional)", height=80)
    make_public = st.checkbox("Playlist öffentlich machen", value=False)
    st.caption(f"Ausgewählte Tracks: {len(selected_uris)}")

    if st.button("Playlist in Spotify erstellen", type="primary"):
        if not playlist_name.strip():
            st.error("Bitte gib einen Namen für die Playlist an.")
            return
        if not selected_uris:
            st.error("Bitte wähle mindestens einen Track aus, bevor du fortfährst.")
            return
        with st.spinner("Playlist wird in Spotify erstellt …"):
            try:
                playlist: SpotifyPlaylist = client.create_playlist(
                    name=playlist_name.strip(),
                    public=make_public,
                    token=token,
                    description=description.strip() or None,
                )
                client.add_tracks_to_playlist(
                    playlist_id=playlist.id,
                    track_uris=list(selected_uris),
                    token=token,
                )
            except Exception as exc:
                st.error(
                    "Die Playlist konnte nicht erstellt werden. "
                    "Bitte versuche es später erneut.",
                )
                st.caption(f"Technische Details: {exc}")
                return
        st.session_state[SPOTIFY_LAST_PLAYLIST_KEY] = {
            "id": playlist.id,
            "name": playlist.name,
            "url": playlist.external_url,
        }
        st.success("Playlist wurde in deinem Spotify-Account erstellt.")
        if playlist.external_url:
            st.markdown(
                f"[In Spotify öffnen]({playlist.external_url})",
                unsafe_allow_html=False,
            )

    last = st.session_state.get(SPOTIFY_LAST_PLAYLIST_KEY)
    if last:
        st.caption(
            f"Zuletzt erstellt: **{last.get('name', '')}**",
        )


def main() -> None:
    st.set_page_config(
        page_title="Spotify-Playlists",
        layout="centered",
        page_icon=None,
    )
    st.markdown(
        "<h1 style='text-align:center;'>Spotify-Playlists</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#6b7280;'>"
        "Verbinde deinen Spotify-Account, suche nach passenden Tracks und "
        "lege daraus Playlists an."
        "</p>",
        unsafe_allow_html=True,
    )
    client = _load_client()
    token = _render_connection_section(client)
    st.markdown("---")
    if client is not None:
        _render_search_section(client, token)
        st.markdown("---")
        _render_playlist_section(client, token)


if __name__ == "__main__":
    main()
