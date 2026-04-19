"""Dedicated Deezer OAuth callback page (no playlist UI on this page).

Streamlit serves this page at ``url_path="deezer_callback"`` (matching
:data:`music_review.integrations.deezer_client.STREAMLIT_DEEZER_PAGE_PATH`).
The page exchanges the Deezer authorization ``code`` for an access token,
restores the user's profile and session snapshot when needed, and finally
redirects the browser back to the page that started the OAuth flow.

Deezer differs from Spotify in two important ways:

* Authorization codes are exchanged via a simple GET (no PKCE verifier).
* Tokens issued with ``offline_access`` never expire, so there is no refresh
  flow to deal with later.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import streamlit as st
from pages.deezer_connection_ui import resolve_deezer_auth_config
from pages.deezer_oauth_kickoff import DEEZER_AUTH_STATE_KEY
from pages.deezer_token_persist import (
    hydrate_deezer_token_from_db_for_active_user,
    persist_deezer_token,
    read_deezer_token_from_session,
)
from pages.page_helpers import (
    DEEZER_OAUTH_RETURN_PAGE_PLAYLIST_HUB,
    DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    apply_deezer_oauth_session_snapshot,
    clear_deezer_oauth_return_page_cookie,
    clear_deezer_oauth_state_cookie,
    clear_deezer_session_snapshot_cookie,
    inject_recommendation_flow_shell_css,
    peek_deezer_oauth_return_page_cookie,
    peek_deezer_oauth_state_cookie,
    peek_deezer_oauth_state_from_context_cookies,
    peek_deezer_session_snapshot_cookie,
    persist_active_profile_slug_cookie,
    render_toolbar,
)

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    default_profiles_dir,
    load_profile,
    normalize_profile_slug,
    post_login_maybe_defer_profile_apply,
)
from music_review.integrations.deezer_client import (
    DeezerClient,
    resolve_deezer_redirect_uri,
)

_STREAMING_CONNECTIONS_PAGE_PATH = "pages/3_Streaming_Verbindungen.py"
# The unified Playlist-Erzeugen page is added in a follow-up task; the constant
# below targets the existing Spotify-Playlists page in the meantime so that
# ``switch_page`` always lands on a registered route.
_PLAYLIST_HUB_PAGE_PATH = "pages/9_Spotify_Playlists.py"

# SHA256 prefix of authorization ``code`` already exchanged or dead.
DEEZER_OAUTH_SPENT_CODE_DIGESTS_KEY = "deezer_oauth_spent_code_digests"
_MAX_SPENT_AUTH_CODE_DIGESTS = 24


def _deezer_authorization_code_digest(code: str) -> str:
    """Stable short digest for deduplicating OAuth authorization codes (no PII)."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]


def _deezer_oauth_spent_digests_list() -> list[str]:
    raw = st.session_state.get(DEEZER_OAUTH_SPENT_CODE_DIGESTS_KEY)
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, str) and x]
    return []


def _deezer_oauth_mark_code_digest_spent(digest: str) -> None:
    """Remember that this authorization code must not be sent to Deezer again."""
    cur = _deezer_oauth_spent_digests_list()
    if digest not in cur:
        cur.append(digest)
    cap = _MAX_SPENT_AUTH_CODE_DIGESTS
    st.session_state[DEEZER_OAUTH_SPENT_CODE_DIGESTS_KEY] = cur[-cap:]


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
    for key in ("code", "state", "error", "error_reason", "error_description"):
        if key in st.query_params:
            del st.query_params[key]


def _split_deezer_oauth_callback_state(state_param: str) -> tuple[str, str | None]:
    """Split Deezer ``state`` into CSRF token and optional profile slug."""
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


def _maybe_restore_deezer_oauth_session_snapshot() -> None:
    """On OAuth return, restore in-tab prefs over profile data from disk."""
    raw = peek_deezer_session_snapshot_cookie()
    if not raw:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return
    apply_deezer_oauth_session_snapshot(st.session_state, data)


def _deezer_browser_url_or_none() -> str | None:
    try:
        raw = st.context.url
    except Exception:
        return None
    return raw if isinstance(raw, str) else None


def _build_deezer_client_for_callback() -> DeezerClient | None:
    """Build a DeezerClient using user creds (if any) or the shared env app."""
    cfg = resolve_deezer_auth_config()
    if cfg is None:
        return None
    browser = _deezer_browser_url_or_none()
    effective = resolve_deezer_redirect_uri(
        configured=cfg.redirect_uri,
        browser_url=browser,
    )
    return DeezerClient(cfg).with_redirect_uri(effective)


def _resolve_post_oauth_target_page() -> str:
    """Return the page path to ``switch_page`` to after a successful OAuth.

    Falls back to the Streaming-Verbindungen page when no return cookie exists.
    """
    target = peek_deezer_oauth_return_page_cookie()
    clear_deezer_oauth_return_page_cookie()
    if target == DEEZER_OAUTH_RETURN_PAGE_PLAYLIST_HUB:
        return _PLAYLIST_HUB_PAGE_PATH
    if target == DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS:
        return _STREAMING_CONNECTIONS_PAGE_PATH
    return _STREAMING_CONNECTIONS_PAGE_PATH


def _redirect_to_post_oauth_target() -> None:
    """Honor the return-page cookie and ``switch_page`` to the right page."""
    st.switch_page(_resolve_post_oauth_target_page())


def _render_idle_callback_message() -> None:
    """When the page is opened without OAuth params, show a friendly hint."""
    inject_recommendation_flow_shell_css()
    render_toolbar("deezer_callback")
    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Deezer-Verbindung</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Diese Seite verarbeitet den R\u00fccksprung '
        "von Deezer nach der Anmeldung.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="rec-callout rec-callout-info">'
        "Es liegen keine Anmeldedaten von Deezer vor. "
        "Starte die Verbindung \u00fcber die Streaming-Verbindungen-Seite."
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button(
        "Zur Verbindungs-Einrichtung",
        type="primary",
        width="stretch",
        key="deezer_callback_to_connections",
    ):
        st.switch_page(_STREAMING_CONNECTIONS_PAGE_PATH)


def _expected_csrf_from_session_or_cookie() -> str | None:
    sess_expected = st.session_state.get(DEEZER_AUTH_STATE_KEY)
    if isinstance(sess_expected, str) and sess_expected.strip():
        return sess_expected.strip()
    cookie_from_cm = peek_deezer_oauth_state_cookie()
    cookie_from_ctx = peek_deezer_oauth_state_from_context_cookies()
    return cookie_from_cm or cookie_from_ctx


def _handle_oauth_callback(client: DeezerClient | None) -> None:
    """Handle Deezer OAuth callback parameters present in the page URL."""
    params = st.query_params
    code = _query_param_single(params.get("code"))
    state = _query_param_single(params.get("state"))
    err = _query_param_single(params.get("error_reason")) or _query_param_single(
        params.get("error"),
    )
    if err:
        _clear_oauth_query_params()
        clear_deezer_oauth_state_cookie()
        st.error(
            "Deezer hat die Anmeldung abgebrochen "
            f"(Grund: {err}). Bitte erneut versuchen.",
        )
        return
    if not code or not state:
        _render_idle_callback_message()
        return

    code_digest = _deezer_authorization_code_digest(code)
    csrf_part, profile_slug_from_state = _split_deezer_oauth_callback_state(state)

    def _cleanup_url_and_oauth_cookies() -> None:
        _clear_oauth_query_params()
        clear_deezer_oauth_state_cookie()
        clear_deezer_session_snapshot_cookie()

    if profile_slug_from_state:
        _restore_profile_from_oauth_callback_slug(profile_slug_from_state)
    _maybe_restore_deezer_oauth_session_snapshot()
    hydrate_deezer_token_from_db_for_active_user()

    if code_digest in _deezer_oauth_spent_digests_list():
        _cleanup_url_and_oauth_cookies()
        st.session_state.pop(DEEZER_AUTH_STATE_KEY, None)
        if read_deezer_token_from_session() is not None:
            _redirect_to_post_oauth_target()
            return
        st.info(
            "Dieser Deezer-Anmeldeschritt wurde schon verarbeitet. "
            "Bitte die Anmeldung erneut starten.",
        )
        return

    if read_deezer_token_from_session() is not None:
        _deezer_oauth_mark_code_digest_spent(code_digest)
        _cleanup_url_and_oauth_cookies()
        st.session_state.pop(DEEZER_AUTH_STATE_KEY, None)
        _redirect_to_post_oauth_target()
        return

    expected_csrf = _expected_csrf_from_session_or_cookie()
    if not expected_csrf or csrf_part != expected_csrf:
        _clear_oauth_query_params()
        clear_deezer_oauth_state_cookie()
        st.error(
            "Sicherheits\u00fcberpr\u00fcfung f\u00fcr den Deezer-Login fehlgeschlagen "
            "(Sitzung abgelaufen oder neuer Tab ohne Cookie). "
            "Bitte erneut bei Deezer anmelden.",
        )
        return

    if client is None:
        _clear_oauth_query_params()
        clear_deezer_oauth_state_cookie()
        st.error(
            "Die Deezer-Verbindung ist nicht konfiguriert. "
            "Bitte hinterlege DEEZER_APP_ID/DEEZER_APP_SECRET in der Umgebung "
            "oder eigene App-Zugangsdaten unter \u201eEigene Deezer-App\u201c.",
        )
        return

    with st.spinner("Deezer-Verbindung wird hergestellt \u2026"):
        try:
            token = client.exchange_code_for_token(code=code)
        except Exception as exc:
            err_lower = str(exc).lower()
            is_wrong_code = "wrong code" in err_lower or (
                "ungültig oder abgelaufen" in err_lower
            )
            if is_wrong_code:
                _deezer_oauth_mark_code_digest_spent(code_digest)
            _clear_oauth_query_params()
            clear_deezer_oauth_state_cookie()
            st.session_state.pop(DEEZER_AUTH_STATE_KEY, None)
            if is_wrong_code:
                st.warning(
                    "Deezer hat diesen Anmeldecode nicht akzeptiert. "
                    "Bitte erneut bei Deezer anmelden.",
                )
            else:
                st.error(
                    f"Deezer-Token konnte nicht abgerufen werden. Details: {exc}",
                )
            return
    persist_deezer_token(token)
    _deezer_oauth_mark_code_digest_spent(code_digest)
    st.session_state.pop(DEEZER_AUTH_STATE_KEY, None)
    _clear_oauth_query_params()
    clear_deezer_oauth_state_cookie()
    clear_deezer_session_snapshot_cookie()
    st.success("Du bist jetzt mit Deezer verbunden.")
    _redirect_to_post_oauth_target()


def main() -> None:
    inject_recommendation_flow_shell_css()
    render_toolbar("deezer_callback")
    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Deezer-Verbindung</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Anmeldedaten von Deezer werden verarbeitet '
        "\u2026</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    client = _build_deezer_client_for_callback()
    _handle_oauth_callback(client)


if __name__ == "__main__":
    main()
