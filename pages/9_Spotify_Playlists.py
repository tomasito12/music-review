from __future__ import annotations

import html
import json
import secrets
from dataclasses import asdict
from typing import Any

import streamlit as st
from pages.neueste_reviews_pool import (
    RECENT_DEFAULT,
    configure_spotify_playlist_logging_from_env,
    ensure_neueste_session_defaults,
    load_newest_reviews_slice,
)
from pages.neueste_spotify_playlist_section import (
    render_neueste_spotify_playlist_section,
)
from pages.page_helpers import (
    SPOTIFY_SURFACE_CONNECTION_UI_KEY,
    apply_spotify_oauth_session_snapshot,
    clear_spotify_oauth_state_cookie,
    clear_spotify_pkce_verifier_cookie,
    clear_spotify_session_snapshot_cookie,
    inject_recommendation_flow_shell_css,
    peek_spotify_oauth_state_cookie,
    peek_spotify_oauth_state_from_context_cookies,
    peek_spotify_pkce_verifier_cookie,
    peek_spotify_pkce_verifier_from_context_cookies,
    peek_spotify_session_snapshot_cookie,
    persist_active_profile_slug_cookie,
    persist_spotify_oauth_state_cookie,
    persist_spotify_pkce_verifier_cookie,
    persist_spotify_session_snapshot_cookie,
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
    SpotifyToken,
    generate_pkce_pair,
    pkce_challenge_from_verifier,
    resolve_spotify_redirect_uri,
)

SPOTIFY_AUTH_STATE_KEY = "spotify_auth_state"
SPOTIFY_PKCE_VERIFIER_KEY = "spotify_pkce_verifier"
SPOTIFY_TOKEN_KEY = "spotify_token"

# Widget session keys to preserve across Spotify OAuth redirect (cookie snapshot).
_SPOTIFY_OAUTH_SNAPSHOT_WIDGET_KEYS: tuple[str, ...] = (
    "spotify-page-pool-count",
    "newest-spotify-taste-orientation",
    "newest-spotify-playlist-name",
    "newest-spotify-playlist-public",
    "newest-spotify-song-count",
)


def _spotify_oauth_session_snapshot_dict() -> dict[str, Any]:
    """Collect taste/filter state from the current session for OAuth round-trip."""
    out: dict[str, Any] = {"snapshot_version": 1}
    fs = st.session_state.get("filter_settings")
    if isinstance(fs, dict):
        out["filter_settings"] = dict(fs)
    cw = st.session_state.get("community_weights_raw")
    if isinstance(cw, dict):
        out["community_weights_raw"] = {
            str(k): float(v) for k, v in cw.items() if isinstance(v, (int, float))
        }
    for key in (
        "selected_communities",
        "artist_flow_selected_communities",
        "genre_flow_selected_communities",
    ):
        val = st.session_state.get(key)
        if isinstance(val, set):
            out[key] = sorted(str(x) for x in val)
        elif isinstance(val, list):
            out[key] = [str(x) for x in val]
    fm = st.session_state.get("flow_mode")
    if fm is None or isinstance(fm, str):
        out["flow_mode"] = fm
    ft = st.session_state.get("free_text_query")
    if isinstance(ft, str):
        out["free_text_query"] = ft
    widgets: dict[str, bool | int | float | str] = {}
    for wkey in _SPOTIFY_OAUTH_SNAPSHOT_WIDGET_KEYS:
        if wkey not in st.session_state:
            continue
        val = st.session_state[wkey]
        if isinstance(val, (bool, int, float, str)):
            widgets[wkey] = val
    if widgets:
        out["widgets"] = widgets
    return out


def _persist_spotify_oauth_session_snapshot() -> None:
    """Persist snapshot in a short-lived cookie (browser outlives server session)."""
    payload = _spotify_oauth_session_snapshot_dict()
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def _utf8_fits(blob: str, limit: int = 3900) -> bool:
        return len(blob.encode("utf-8")) <= limit

    if not _utf8_fits(raw):
        payload.pop("widgets", None)
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if not _utf8_fits(raw):
        return
    persist_spotify_session_snapshot_cookie(raw)


def _maybe_restore_spotify_oauth_session_snapshot() -> None:
    """On OAuth return, restore in-tab prefs over profile data from disk."""
    if not _query_param_single(st.query_params.get("code")):
        return
    raw = peek_spotify_session_snapshot_cookie()
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    apply_spotify_oauth_session_snapshot(st.session_state, data)


def _spotify_page_shell_css() -> None:
    """Shared typography and hero styles (same shell as Empfehlungen / Neueste)."""
    inject_recommendation_flow_shell_css()


def _section_divider() -> None:
    st.markdown(
        '<div class="rec-results-divider" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _section_label(text: str) -> None:
    st.markdown(
        f'<p class="rec-sort-section-label">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )


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


def _redirect_uri_mismatch_hint_html(*, effective: str, browser: str) -> str:
    """HTML body for the redirect URI mismatch callout (values must be escaped)."""
    eff_e = html.escape(effective)
    br_e = html.escape(browser)
    return (
        "An Spotify wird als <strong>redirect_uri</strong> nur "
        "<code>SPOTIFY_REDIRECT_URI</code> aus der "
        f"<code>.env</code> geschickt: <code>{eff_e}</code>. "
        f"Dein Browser zeigt gerade <code>{br_e}</code>. "
        "Öffne die Spotify-Seite <strong>über dieselbe URL wie in der</strong> "
        "<code>.env</code>, damit der Rücksprung nach der Anmeldung zur "
        "laufenden Sitzung passt. Im Spotify-Dashboard muss <strong>genau</strong> "
        "diese <code>.env</code>-Adresse unter Redirect URIs stehen."
    )


def _load_client_and_redirect_hint() -> tuple[SpotifyClient | None, str | None]:
    """Load Spotify client; OAuth uses ``SPOTIFY_REDIRECT_URI`` unless overridden."""
    try:
        cfg = SpotifyAuthConfig.from_env()
    except Exception as exc:
        detail = html.escape(str(exc))
        st.markdown(
            '<div class="rec-callout rec-callout-warn">'
            "Spotify-Konfiguration fehlt oder ist unvollständig "
            "(Client-ID/Redirect-URL). Bitte <code>.env</code> prüfen."
            f"<br/><span style='font-size:0.82em;opacity:0.9'>"
            f"Technische Details: {detail}</span></div>",
            unsafe_allow_html=True,
        )
        return None, None
    browser = _spotify_browser_url_or_none()
    effective = resolve_spotify_redirect_uri(
        configured=cfg.redirect_uri,
        browser_url=browser,
    )
    client = SpotifyClient(cfg).with_redirect_uri(effective)
    hint: str | None = None
    if browser and not _oauth_redirect_urls_equivalent(browser, effective):
        hint = _redirect_uri_mismatch_hint_html(
            effective=effective,
            browser=browser,
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


def _spotify_pkce_verifier_raw() -> str | None:
    """Return PKCE verifier from session or browser cookies (OAuth return path)."""
    raw = st.session_state.get(SPOTIFY_PKCE_VERIFIER_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return (
        peek_spotify_pkce_verifier_from_context_cookies()
        or peek_spotify_pkce_verifier_cookie()
    )


def _spotify_code_challenge_for_authorize() -> str | None:
    """S256 challenge for the authorize URL, or None if verifier is missing."""
    ver = _spotify_pkce_verifier_raw()
    return pkce_challenge_from_verifier(ver) if ver else None


def _clear_spotify_oauth_browser_cookies() -> None:
    """Remove OAuth state and PKCE cookies and drop verifier from session."""
    clear_spotify_oauth_state_cookie()
    clear_spotify_pkce_verifier_cookie()
    st.session_state.pop(SPOTIFY_PKCE_VERIFIER_KEY, None)


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
        _clear_spotify_oauth_browser_cookies()
        clear_spotify_session_snapshot_cookie()
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
        _clear_spotify_oauth_browser_cookies()
        st.error(
            "Sicherheitsüberprüfung für den Spotify-Login fehlgeschlagen "
            "(Sitzung abgelaufen oder neuer Tab ohne Cookie). "
            "Bitte „Mit Spotify verbinden“ erneut wählen.",
        )
        return
    if profile_slug_from_state:
        _restore_profile_from_oauth_callback_slug(profile_slug_from_state)
    pkce_verifier = _spotify_pkce_verifier_raw()
    if not pkce_verifier:
        _clear_oauth_query_params()
        _clear_spotify_oauth_browser_cookies()
        st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
        st.error(
            "Spotify-Login: interne PKCE-Daten fehlen (z. B. neuer Tab oder "
            "Cookies blockiert). Bitte „Mit Spotify verbinden“ erneut starten.",
        )
        return
    with st.spinner("Spotify-Verbindung wird hergestellt …"):
        try:
            token = client.exchange_code_for_token(
                code=code,
                code_verifier=pkce_verifier,
            )
        except Exception as exc:
            _clear_oauth_query_params()
            _clear_spotify_oauth_browser_cookies()
            st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
            st.error(f"Spotify-Token konnte nicht abgerufen werden. Details: {exc}")
            st.caption(
                "Typische Ursachen: Redirect-URI weicht von der Spotify-App ab, "
                "Authorization-Code wurde schon einmal verwendet (Seite mit ?code= "
                "nicht neu laden), oder Netzwerkfehler."
            )
            return
    _store_token(token)
    st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
    _clear_oauth_query_params()
    _clear_spotify_oauth_browser_cookies()
    clear_spotify_session_snapshot_cookie()
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
    code_challenge: str,
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
        client.build_authorize_url(
            state=oauth_state,
            code_challenge=code_challenge,
        ),
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
    """Show Spotify OAuth UI only when needed (connected, OAuth flow, or surfaced)."""
    if client is None:
        st.markdown(
            '<div class="rec-callout rec-callout-info">'
            "Diese Seite benötigt eine gültige Spotify-Konfiguration, um "
            "Playlists zu erstellen.</div>",
            unsafe_allow_html=True,
        )
        return None

    token = _get_stored_token()
    pending_state = _normalized_spotify_oauth_pending_state(
        st.session_state.get(SPOTIFY_AUTH_STATE_KEY),
    )
    surface = bool(st.session_state.get(SPOTIFY_SURFACE_CONNECTION_UI_KEY))
    must_show = (
        token is not None
        or redirect_hint is not None
        or pending_state is not None
        or surface
    )
    if not must_show:
        return None

    if token is not None:
        _section_label("Verbindung zu Spotify")
        col_status, col_action = st.columns([3, 1])
        with col_status:
            st.success("Mit Spotify verbunden.")
        with col_action:
            if st.button("Verbindung trennen", key="spotify_disconnect"):
                st.session_state.pop(SPOTIFY_TOKEN_KEY, None)
                st.session_state.pop(SPOTIFY_SURFACE_CONNECTION_UI_KEY, None)
                _clear_spotify_oauth_browser_cookies()
                st.rerun()
        return token

    with st.expander("Verbindung zu Spotify", expanded=True):
        if redirect_hint:
            st.markdown(
                f'<div class="rec-callout rec-callout-info">{redirect_hint}</div>',
                unsafe_allow_html=True,
            )

        # OAuth start is a two-step flow (primary button, then link). Streamlit only
        # reports the primary button as clicked for a single rerun; CookieManager or
        # other widgets can rerun the script immediately, which would otherwise hide
        # the link and show only the "not connected" info again.
        if pending_state is not None:
            code_challenge = _spotify_code_challenge_for_authorize()
            if not code_challenge:
                st.error(
                    "OAuth-Daten sind unvollständig (PKCE fehlt). "
                    "Bitte „Mit Spotify verbinden“ erneut wählen.",
                )
                st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
                _clear_spotify_oauth_browser_cookies()
                st.rerun()
                return None
            _render_spotify_oauth_continue_ui(
                client,
                oauth_state=_spotify_oauth_state_for_authorize_url(pending_state),
                code_challenge=code_challenge,
            )
            if st.button("Login abbrechen", key="spotify_oauth_cancel"):
                st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
                _clear_spotify_oauth_browser_cookies()
                st.rerun()
            return None

        if st.button("Mit Spotify verbinden", type="primary"):
            _persist_spotify_oauth_session_snapshot()
            state = secrets.token_urlsafe(32)
            pkce_verifier, pkce_challenge = generate_pkce_pair()
            st.session_state[SPOTIFY_AUTH_STATE_KEY] = state
            st.session_state[SPOTIFY_PKCE_VERIFIER_KEY] = pkce_verifier
            persist_spotify_oauth_state_cookie(state)
            persist_spotify_pkce_verifier_cookie(pkce_verifier)
            _render_spotify_oauth_continue_ui(
                client,
                oauth_state=_spotify_oauth_state_for_authorize_url(state),
                code_challenge=pkce_challenge,
            )
        else:
            st.markdown(
                '<div class="rec-callout rec-callout-info">'
                "Noch nicht mit Spotify verbunden. Klicke auf "
                "„Mit Spotify verbinden“, um den Login zu starten.</div>",
                unsafe_allow_html=True,
            )
    return None


def main() -> None:
    configure_spotify_playlist_logging_from_env()
    _spotify_page_shell_css()
    render_toolbar("spotify_playlists")

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Spotify-Playlists</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Generiere eine Spotify-Playlist aus den neuesten '
        "Rezensionen - <br/>passend zu Deinem Musikgeschmack.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    client, redirect_hint = _load_client_and_redirect_hint()
    _maybe_restore_spotify_oauth_session_snapshot()
    if client is not None:
        _handle_oauth_callback(client)
    if _get_stored_token() is not None:
        st.session_state.pop(SPOTIFY_SURFACE_CONNECTION_UI_KEY, None)
    _render_connection_section(client, redirect_hint)
    _section_divider()

    ensure_neueste_session_defaults()
    n_pool = st.slider(
        "Wie viele der letzten Rezensionen sollen bei der Erstellung deiner "
        "Playlist berücksichtigt werden?",
        min_value=5,
        max_value=50,
        value=RECENT_DEFAULT,
        step=1,
        key="spotify-page-pool-count",
    )
    reviews = load_newest_reviews_slice(n_pool)
    if not reviews:
        st.markdown(
            '<div class="rec-callout rec-callout-warn">'
            "Keine Reviews gefunden. Pfad prüfen: <code>data/reviews.jsonl</code> "
            "(ggf. Scraping ausführen).</div>",
            unsafe_allow_html=True,
        )
    else:
        render_neueste_spotify_playlist_section(reviews=reviews)


if __name__ == "__main__":
    main()
