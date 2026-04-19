from __future__ import annotations

import hashlib
import html
import json
from typing import Any

import streamlit as st
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
    SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    apply_spotify_oauth_session_snapshot,
    clear_spotify_oauth_return_page_cookie,
    clear_spotify_oauth_state_cookie,
    clear_spotify_pkce_verifier_cookie,
    clear_spotify_session_snapshot_cookie,
    inject_recommendation_flow_shell_css,
    peek_spotify_oauth_return_page_cookie,
    peek_spotify_oauth_state_cookie,
    peek_spotify_oauth_state_from_context_cookies,
    peek_spotify_session_snapshot_cookie,
    persist_active_profile_slug_cookie,
    render_toolbar,
)
from pages.spotify_connection_ui import (
    try_load_user_spotify_config as _try_load_user_spotify_config,
)
from pages.spotify_connection_ui import (
    user_has_spotify_credentials as _user_has_spotify_credentials,
)
from pages.spotify_oauth_kickoff import (
    SPOTIFY_AUTH_STATE_KEY,
    SPOTIFY_PKCE_VERIFIER_KEY,
    spotify_pkce_verifier_raw,
)
from pages.spotify_token_persist import (
    hydrate_spotify_token_from_db_for_active_user,
    persist_spotify_token,
    read_spotify_token_from_session,
)

from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_db import (
    load_spotify_credentials,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    default_profiles_dir,
    load_profile,
    normalize_profile_slug,
    post_login_maybe_defer_profile_apply,
)
from music_review.integrations.spotify_client import (
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyConfigError,
    SpotifyToken,
    resolve_spotify_redirect_uri,
)

# Path of the Streaming-Verbindungen page used for CTA links and OAuth-return.
_STREAMING_CONNECTIONS_PAGE_PATH = "pages/3_Streaming_Verbindungen.py"

# SHA256 prefix of authorization ``code`` already exchanged or dead (invalid_grant).
SPOTIFY_OAUTH_SPENT_CODE_DIGESTS_KEY = "spotify_oauth_spent_code_digests"
_MAX_SPENT_AUTH_CODE_DIGESTS = 24


def _spotify_authorization_code_digest(code: str) -> str:
    """Stable short digest for deduplicating OAuth authorization codes (no PII)."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]


def _spotify_oauth_spent_digests_list() -> list[str]:
    raw = st.session_state.get(SPOTIFY_OAUTH_SPENT_CODE_DIGESTS_KEY)
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, str) and x]
    return []


def _spotify_oauth_mark_code_digest_spent(digest: str) -> None:
    """Remember that this authorization code must not be sent to Spotify again."""
    cur = _spotify_oauth_spent_digests_list()
    if digest not in cur:
        cur.append(digest)
    cap = _MAX_SPENT_AUTH_CODE_DIGESTS
    st.session_state[SPOTIFY_OAUTH_SPENT_CODE_DIGESTS_KEY] = cur[-cap:]


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
        "diese <code>.env</code>-Adresse unter Redirect URIs stehen. "
        "Wichtig: <strong>localhost</strong> und <strong>127.0.0.1</strong> sind "
        "für Cookies getrennte Hosts; nutze dieselbe Form wie in der Redirect-URI."
    )


def _try_spotify_auth_config_for_slug(slug: str) -> SpotifyAuthConfig | None:
    """Load Spotify OAuth config from DB credentials for a profile slug."""
    try:
        safe = normalize_profile_slug(slug)
    except ValueError:
        return None
    conn = get_db_connection()
    creds = load_spotify_credentials(conn, safe)
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


def _oauth_profile_slug_from_state_param(state_param: str) -> str | None:
    """Return the profile slug embedded in authorize ``state``, if any."""
    _csrf, slug = _split_spotify_oauth_callback_state(state_param)
    return slug


def _spotify_oauth_callback_query_present() -> bool:
    """True when the URL looks like a Spotify OAuth redirect (?code= and ?state=)."""
    code = _query_param_single(st.query_params.get("code"))
    state = _query_param_single(st.query_params.get("state"))
    return bool(code and state)


def _load_client_and_redirect_hint() -> tuple[SpotifyClient | None, str | None]:
    """Load Spotify client from DB (callback slug, then session) or .env fallback.

    On OAuth return the browser may not have restored the Plattenradar session yet.
    The authorize ``state`` embeds the profile slug; we load that user's Spotify app
    credentials from the DB so the authorization code exchanges with the same client.
    """
    cfg: SpotifyAuthConfig | None = None
    if _spotify_oauth_callback_query_present():
        state_raw = _query_param_single(st.query_params.get("state"))
        if isinstance(state_raw, str) and state_raw:
            slug_from_state = _oauth_profile_slug_from_state_param(state_raw)
            if slug_from_state:
                cfg = _try_spotify_auth_config_for_slug(slug_from_state)
    if cfg is None:
        cfg = _try_load_user_spotify_config()
    if cfg is None:
        try:
            cfg = SpotifyAuthConfig.from_env()
        except Exception:
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
    return read_spotify_token_from_session()


def _store_token(token: SpotifyToken) -> None:
    persist_spotify_token(token)


def _query_param_single(raw: Any) -> str | None:
    """Normalize Streamlit query param value to a single string."""
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        return str(raw[0])
    return str(raw)


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
    post_login_maybe_defer_profile_apply(
        st.session_state,
        profile_slug=safe,
        server_profile=data,
    )
    persist_active_profile_slug_cookie(safe)


def _maybe_redirect_after_successful_oauth() -> None:
    """Honor the return-page cookie and ``switch_page`` if the user came elsewhere."""
    target = peek_spotify_oauth_return_page_cookie()
    clear_spotify_oauth_return_page_cookie()
    if target == SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS:
        st.switch_page(_STREAMING_CONNECTIONS_PAGE_PATH)


def _handle_oauth_callback(client: SpotifyClient) -> None:
    """Handle OAuth callback parameters present in the page URL."""
    params = st.query_params
    code = _query_param_single(params.get("code"))
    state = _query_param_single(params.get("state"))
    if not code or not state:
        return
    code_digest = _spotify_authorization_code_digest(code)

    def _cleanup_url_and_oauth_cookies() -> None:
        _clear_oauth_query_params()
        _clear_spotify_oauth_browser_cookies()
        clear_spotify_session_snapshot_cookie()

    csrf_part, profile_slug_from_state = _split_spotify_oauth_callback_state(state)

    if code_digest in _spotify_oauth_spent_digests_list():
        _cleanup_url_and_oauth_cookies()
        st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
        if _get_stored_token() is not None:
            _maybe_redirect_after_successful_oauth()
            return
        st.info(
            "Dieser Spotify-Anmeldeschritt wurde schon verarbeitet (oder der Code "
            "war nur einmal gültig). Bitte die Seite ohne alte URL-Parameter neu laden "
            "und unten erneut bei Spotify anmelden."
        )
        return

    # Spotify authorization codes are single-use; Streamlit may rerun with ?code=
    # still visible before the URL is cleaned up — skip a second exchange.
    if _get_stored_token() is not None:
        _spotify_oauth_mark_code_digest_spent(code_digest)
        _cleanup_url_and_oauth_cookies()
        st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
        _maybe_redirect_after_successful_oauth()
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
            "Bitte unten erneut bei Spotify anmelden.",
        )
        return
    if profile_slug_from_state:
        _restore_profile_from_oauth_callback_slug(profile_slug_from_state)
    pkce_verifier = spotify_pkce_verifier_raw()
    if not pkce_verifier:
        _clear_oauth_query_params()
        _clear_spotify_oauth_browser_cookies()
        st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
        st.error(
            "Spotify-Login: interne PKCE-Daten fehlen (z. B. neuer Tab oder "
            "Cookies blockiert). Bitte unten erneut bei Spotify anmelden.",
        )
        return
    with st.spinner("Spotify-Verbindung wird hergestellt …"):
        try:
            token = client.exchange_code_for_token(
                code=code,
                code_verifier=pkce_verifier,
            )
        except Exception as exc:
            err_lower = str(exc).lower()
            is_invalid_grant = "invalid_grant" in err_lower or (
                "invalid authorization code" in err_lower
            )
            if is_invalid_grant:
                _spotify_oauth_mark_code_digest_spent(code_digest)
            _clear_oauth_query_params()
            _clear_spotify_oauth_browser_cookies()
            st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
            if is_invalid_grant:
                st.warning(
                    "Spotify hat diesen Anmeldecode nicht mehr akzeptiert "
                    "(meist: zweiter Aufruf nach erfolgreicher Anmeldung oder "
                    "Seite mit altem Link neu geladen). "
                    "Bitte unten erneut bei Spotify anmelden."
                )
            else:
                st.error(f"Spotify-Token konnte nicht abgerufen werden. Details: {exc}")
                st.caption(
                    "Typische Ursachen: Redirect-URI weicht von der Spotify-App ab, "
                    "oder Netzwerkfehler. Bei wiederholtem Fehler unten erneut "
                    "bei Spotify anmelden."
                )
            return
    # Persist token before clearing URL so a fast Streamlit rerun cannot retry the code.
    _store_token(token)
    _spotify_oauth_mark_code_digest_spent(code_digest)
    st.session_state.pop(SPOTIFY_AUTH_STATE_KEY, None)
    _clear_oauth_query_params()
    _clear_spotify_oauth_browser_cookies()
    clear_spotify_session_snapshot_cookie()
    st.success("Du bist jetzt mit Spotify verbunden.")
    _maybe_redirect_after_successful_oauth()


def _should_show_missing_connection_callout(
    *,
    client: SpotifyClient | None,
    has_user_creds: bool,
    oauth_callback_pending: bool,
) -> bool:
    """True when the page must redirect to the Streaming-Verbindungen page.

    OAuth callbacks must be processed here even when a client failed to load,
    so we never gate on missing creds while ``?code=`` is present in the URL.
    """
    if oauth_callback_pending:
        return False
    return client is None or not has_user_creds


def _render_missing_connection_callout() -> None:
    """Show a CTA pointing the user to the Streaming-Verbindungen page."""
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Für diese Seite musst du zuerst eine Spotify-Verbindung einrichten."
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button(
        "Zur Verbindungs-Einrichtung",
        type="primary",
        width="stretch",
        key="spotify_playlists_to_connections",
    ):
        st.switch_page(_STREAMING_CONNECTIONS_PAGE_PATH)


def _render_connection_redirect_hint(redirect_hint: str | None) -> None:
    """Display the optional redirect URI mismatch hint when a token is missing."""
    if not redirect_hint:
        return
    st.markdown(
        f'<div class="rec-callout rec-callout-info">{redirect_hint}</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    configure_spotify_playlist_logging_from_env()
    _spotify_page_shell_css()
    render_toolbar("spotify_playlists")

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Spotify-Playlists</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Generiere eine Spotify-Playlist - aus den '
        "neuesten Rezensionen oder dem gesamten Archiv, <br/>passend zu Deinem "
        "Musikgeschmack.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    oauth_pending = _spotify_oauth_callback_query_present()
    has_user_creds = _user_has_spotify_credentials()
    client, redirect_hint = _load_client_and_redirect_hint()

    if _should_show_missing_connection_callout(
        client=client,
        has_user_creds=has_user_creds,
        oauth_callback_pending=oauth_pending,
    ):
        _render_missing_connection_callout()
        return

    _maybe_restore_spotify_oauth_session_snapshot()
    hydrate_spotify_token_from_db_for_active_user()
    if client is not None:
        _handle_oauth_callback(client)
    if _get_stored_token() is None:
        _render_connection_redirect_hint(redirect_hint)
    _section_divider()

    ensure_neueste_session_defaults()
    tab_newest, tab_archive = st.tabs(["Neueste Rezensionen", "Gesamtes Archiv"])
    with tab_newest:
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
    with tab_archive:
        render_archive_spotify_playlist_section()


if __name__ == "__main__":
    main()
