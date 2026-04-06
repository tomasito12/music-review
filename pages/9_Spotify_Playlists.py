from __future__ import annotations

import logging
import secrets
from dataclasses import asdict
from typing import Any

import streamlit as st
from pages.neueste_reviews_pool import (
    RECENT_DEFAULT,
    configure_spotify_playlist_logging_from_env,
    ensure_neueste_session_defaults,
    fetch_newest_reviews_pool,
)
from pages.neueste_spotify_playlist_section import (
    render_neueste_spotify_playlist_section,
)
from pages.page_helpers import (
    clear_spotify_oauth_state_cookie,
    peek_spotify_oauth_state_cookie,
    peek_spotify_oauth_state_from_context_cookies,
    persist_active_profile_slug_cookie,
    persist_spotify_oauth_state_cookie,
    render_toolbar,
)

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    default_profiles_dir,
    load_profile,
    normalize_profile_slug,
)
from music_review.integrations.spotify_client import (
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyPlaylist,
    SpotifyToken,
    resolve_spotify_redirect_uri,
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

_LOGGER = logging.getLogger(__name__)


def _spotify_browser_url_or_none() -> str | None:
    """Return the Streamlit-reported browser URL, or None if unavailable."""
    try:
        raw = st.context.url
    except Exception:
        return None
    return raw if isinstance(raw, str) else None


def _oauth_redirect_urls_equivalent(a: str, b: str) -> bool:
    """Compare redirect URLs loosely (trim, ignore trailing slash on path)."""
    return a.strip().rstrip("/") == b.strip().rstrip("/")


def _load_client_and_redirect_hint() -> tuple[SpotifyClient | None, str | None]:
    """Load Spotify client; OAuth uses ``SPOTIFY_REDIRECT_URI`` unless overridden."""
    try:
        cfg = SpotifyAuthConfig.from_env()
    except Exception as exc:
        st.warning(
            "Spotify-Konfiguration fehlt oder ist unvollständig "
            "(Client-ID/Redirect-URL). Bitte `.env` prüfen.",
        )
        st.caption(f"Technische Details: {exc}")
        return None, None
    browser = _spotify_browser_url_or_none()
    effective = resolve_spotify_redirect_uri(
        configured=cfg.redirect_uri,
        browser_url=browser,
    )
    client = SpotifyClient(cfg).with_redirect_uri(effective)
    hint: str | None = None
    if browser and not _oauth_redirect_urls_equivalent(browser, effective):
        hint = (
            "An Spotify wird als **redirect_uri** nur `SPOTIFY_REDIRECT_URI` aus der "
            f"`.env` geschickt: `{effective}`. Dein Browser zeigt gerade `{browser}`. "
            "Öffne die Spotify-Seite **über dieselbe URL wie in der `.env`**, damit "
            "der Rücksprung nach der Anmeldung zur laufenden Sitzung passt. "
            "Im Spotify-Dashboard muss **genau** diese `.env`-Adresse unter "
            "Redirect URIs stehen."
        )
    return client, hint


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


def _split_spotify_oauth_callback_state(state_param: str) -> tuple[str, str | None]:
    """Split Spotify ``state`` into CSRF token and optional profile slug.

    ``secrets.token_urlsafe`` does not produce ``.``, so a single dot separates
    CSRF (left) from a normalized profile slug (right). Legacy states have no
    dot: the full string is the CSRF token.
    """
    if "." not in state_param:
        return state_param, None
    left, right = state_param.split(".", 1)
    if not left or not right:
        return state_param, None
    try:
        normalize_profile_slug(right)
    except ValueError:
        return state_param, None
    return left, right


def _spotify_oauth_state_for_authorize_url(csrf: str) -> str:
    """Build ``state`` query value: CSRF plus profile slug when logged in."""
    slug_any = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(slug_any, str) or not slug_any.strip():
        return csrf
    try:
        safe = normalize_profile_slug(slug_any.strip())
    except ValueError:
        return csrf
    return f"{csrf}.{safe}"


def _restore_profile_from_oauth_callback_slug(slug: str) -> None:
    """Re-hydrate session and profile cookie when browser dropped profile cookie."""
    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        return
    try:
        safe = normalize_profile_slug(slug)
    except ValueError:
        return
    data = load_profile(default_profiles_dir(), safe)
    if data is None:
        return
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = safe
    apply_profile_to_session(st.session_state, data)
    persist_active_profile_slug_cookie(safe)


def _handle_oauth_callback(client: SpotifyClient) -> None:
    """Handle OAuth callback parameters present in the page URL."""
    params = st.query_params
    code = _query_param_single(params.get("code"))
    state = _query_param_single(params.get("state"))
    if not code or not state:
        return
    csrf_part, profile_slug_from_state = _split_spotify_oauth_callback_state(state)
    # Spotify authorization codes are single-use; Streamlit may rerun with ?code=
    # still visible before the URL is cleaned up — skip a second exchange.
    if _get_stored_token() is not None:
        _clear_oauth_query_params()
        clear_spotify_oauth_state_cookie()
        st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
        return
    sess_expected = st.session_state.get(SPOTIFY_AUTH_STATE_KEY)
    cookie_from_cm = peek_spotify_oauth_state_cookie()
    cookie_from_ctx = peek_spotify_oauth_state_from_context_cookies()
    cookie_expected = cookie_from_cm or cookie_from_ctx
    if isinstance(sess_expected, str) and sess_expected.strip():
        expected_csrf = sess_expected.strip()
    elif cookie_expected:
        expected_csrf = cookie_expected
    else:
        expected_csrf = None
    if not expected_csrf or csrf_part != expected_csrf:
        _clear_oauth_query_params()
        clear_spotify_oauth_state_cookie()
        st.error(
            "Sicherheitsüberprüfung für den Spotify-Login fehlgeschlagen "
            "(Sitzung abgelaufen oder neuer Tab ohne Cookie). "
            "Bitte „Mit Spotify verbinden“ erneut wählen.",
        )
        return
    if profile_slug_from_state:
        _restore_profile_from_oauth_callback_slug(profile_slug_from_state)
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


def _normalized_spotify_oauth_pending_state(raw: object) -> str | None:
    """Return stripped OAuth state if ``raw`` is a non-empty string, otherwise None."""
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _render_spotify_oauth_continue_ui(
    client: SpotifyClient,
    *,
    oauth_state: str,
) -> None:
    """Show redirect hint, Spotify link, and short guidance mid-OAuth."""
    st.caption(
        "An Spotify wird **`SPOTIFY_REDIRECT_URI` aus der `.env`** verwendet: "
        f"`{client.redirect_uri}`. Dieselbe Zeichenkette muss im "
        "[Spotify Developer Dashboard](https://developer.spotify.com/dashboard) "
        "unter **Redirect URIs** stehen (ohne Leerzeichen am Ende, in der Regel "
        "**ohne** Schrägstrich am Ende des Pfads)."
    )
    st.link_button(
        "Zum Spotify-Login wechseln",
        client.build_authorize_url(state=oauth_state),
        use_container_width=True,
    )
    st.caption(
        "Als Nächstes bei Spotify anmelden und freigeben. "
        "Dieser Link bleibt sichtbar, bis du dich angemeldet hast oder abbrichst."
    )


def _render_connection_section(
    client: SpotifyClient | None,
    redirect_hint: str | None,
) -> SpotifyToken | None:
    st.subheader("Verbindung zu Spotify")
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
                clear_spotify_oauth_state_cookie()
                st.rerun()
        return token

    if redirect_hint:
        st.info(redirect_hint)

    # OAuth start is a two-step flow (primary button, then link). Streamlit only
    # reports the primary button as clicked for a single rerun; CookieManager or
    # other widgets can rerun the script immediately, which would otherwise hide
    # the link and show only the "not connected" info again.
    pending_state = _normalized_spotify_oauth_pending_state(
        st.session_state.get(SPOTIFY_AUTH_STATE_KEY),
    )
    if pending_state is not None:
        _render_spotify_oauth_continue_ui(
            client,
            oauth_state=_spotify_oauth_state_for_authorize_url(pending_state),
        )
        if st.button("Login abbrechen", key="spotify_oauth_cancel"):
            st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
            clear_spotify_oauth_state_cookie()
            st.rerun()
        return None

    if st.button("Mit Spotify verbinden", type="primary"):
        state = secrets.token_urlsafe(32)
        st.session_state[SPOTIFY_AUTH_STATE_KEY] = state
        persist_spotify_oauth_state_cookie(state)
        _render_spotify_oauth_continue_ui(
            client,
            oauth_state=_spotify_oauth_state_for_authorize_url(state),
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
                _LOGGER.info(
                    "manual spotify playlist: create name=%r public=%s n_tracks=%s",
                    playlist_name.strip(),
                    make_public,
                    len(selected_uris),
                )
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
                _LOGGER.info(
                    "manual spotify playlist: done playlist_id=%s url=%r",
                    playlist.id,
                    playlist.external_url,
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
    configure_spotify_playlist_logging_from_env()
    render_toolbar("spotify_playlists")

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
    client, redirect_hint = _load_client_and_redirect_hint()
    token = _render_connection_section(client, redirect_hint)
    st.markdown("---")

    ensure_neueste_session_defaults()
    st.subheader("Playlist aus neuesten Rezensionen")
    st.caption(
        "Gleicher Datenpool und Gewichtung wie auf der Seite „Neueste Rezensionen“ "
        "(Community-Auswahl über die Profilleiste in der Seitenleiste oder auf "
        "den anderen Seiten)."
    )
    with st.container(border=True):
        n_show = st.slider(
            "Wie viele der neuesten Alben einbeziehen",
            min_value=5,
            max_value=50,
            value=RECENT_DEFAULT,
            step=1,
            key="spotify-page-neueste-n-show",
            label_visibility="visible",
        )
    reviews, ranked_rows = fetch_newest_reviews_pool(n_show)
    if not reviews:
        st.info(
            "Keine Rezensionen im lokalen Corpus. Pfad prüfen: data/reviews.jsonl "
            "(ggf. Scraping ausführen)."
        )
    else:
        render_neueste_spotify_playlist_section(
            reviews=reviews,
            ranked_rows=ranked_rows,
        )

    st.markdown("---")
    if client is not None:
        _render_search_section(client, token)
        st.markdown("---")
        _render_playlist_section(client, token)


if __name__ == "__main__":
    main()
