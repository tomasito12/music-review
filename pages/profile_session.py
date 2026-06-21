"""Profile login, cookies, and sidebar UI for Streamlit pages."""

from __future__ import annotations

import contextlib
from typing import Any

from pages._streamlit_ctx import st
from pages.filter_state import (
    FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY,
    WIZARD_ACCOUNT_SAVE_INTENT_KEY,
    get_selected_communities,
)

from music_review.dashboard.user_db import (
    create_session_token,
    delete_session_token,
    load_user_profile,
    validate_session_token,
)
from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_COOKIE_NAME,
    ACTIVE_PROFILE_SESSION_KEY,
    LOGIN_GUEST_SESSION_PINNED_KEY,
    LOGIN_PROFILE_MERGE_PENDING_KEY,
    ProfileHydrationResult,
    build_profile_payload,
    default_profiles_dir,
    ensure_active_profile_hydrated,
    normalize_profile_slug,
    post_login_maybe_defer_profile_apply,
    save_profile,
)

# Browser cookie for session-token-based login (replaces plain slug cookie).
SESSION_TOKEN_COOKIE_NAME = "mr_session_token"

# CookieManager uses a fixed element key; only one instance per session.
_PROFILE_COOKIE_MANAGER_STATE_KEY = "_mr_profile_cookie_manager_singleton"


def build_session_profile_payload(*, profile_slug: str) -> dict[str, Any]:
    """Assemble profile JSON from the current Streamlit session (taste + filters)."""
    selected = get_selected_communities()
    fs = st.session_state.get("filter_settings")
    if not isinstance(fs, dict):
        fs = {}
    weights = st.session_state.get("community_weights_raw")
    if not isinstance(weights, dict):
        weights = {}
    return build_profile_payload(
        profile_slug=profile_slug,
        flow_mode=st.session_state.get("flow_mode"),
        selected_communities=selected,
        filter_settings=fs,
        community_weights_raw=weights,
    )


def persist_active_profile_from_session() -> str | None:
    """Write taste + filter session to profile JSON when a profile slug is active."""
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        slug = normalize_profile_slug(raw)
    except ValueError:
        return None
    profiles_dir = default_profiles_dir()
    payload = build_session_profile_payload(profile_slug=slug)
    save_profile(profiles_dir, slug, payload)
    st.session_state.pop(LOGIN_GUEST_SESSION_PINNED_KEY, None)
    return slug


def save_current_profile_to_disk() -> None:
    """Persist current session settings under the active profile slug."""
    slug = persist_active_profile_from_session()
    if slug is None:
        st.warning("Kein Profil aktiv -- bitte zuerst anmelden.")
        return
    st.success(f"Profil '{slug}' gespeichert.")


def logout_active_profile() -> None:
    """Sign out: invalidate session token, clear cookie, clear taste keys."""
    from pages import page_helpers as ph

    ph._invalidate_current_session_token()
    st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
    st.session_state.pop(LOGIN_PROFILE_MERGE_PENDING_KEY, None)
    st.session_state.pop(LOGIN_GUEST_SESSION_PINNED_KEY, None)
    st.session_state.pop(FILTER_ACCOUNT_SAVE_PROMPT_ACTIVE_KEY, None)
    st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
    ph.clear_session_token_cookie()
    ph.reset_taste_preferences()


def profile_cookie_manager() -> Any:
    """Shared CookieManager so the component is not instantiated twice in one run."""
    import extra_streamlit_components as stx

    existing = st.session_state.get(_PROFILE_COOKIE_MANAGER_STATE_KEY)
    if existing is not None:
        return existing
    cm = stx.CookieManager(key="mr_profile_cookie_mgr")
    st.session_state[_PROFILE_COOKIE_MANAGER_STATE_KEY] = cm
    return cm


def _safe_cookie_manager_delete(cm: Any, cookie_name: str, *, key: str) -> None:
    """Call CookieManager.delete without failing when the name is absent locally."""
    with contextlib.suppress(KeyError):
        cm.delete(cookie_name, key=key)


def persist_session_token_cookie(token: str) -> None:
    """Store a session token in the browser (same-site lax, 30 days)."""
    if not isinstance(token, str) or not token.strip():
        return
    from pages import page_helpers as ph

    cm = ph.profile_cookie_manager()
    cm.set(
        SESSION_TOKEN_COOKIE_NAME,
        token,
        key="mr_cookie_set_session_token",
        max_age=60.0 * 60 * 24 * 30,
        same_site="lax",
    )


def clear_session_token_cookie() -> None:
    """Remove the session-token cookie (logout or invalid token)."""
    from pages import page_helpers as ph

    cm = ph.profile_cookie_manager()
    _safe_cookie_manager_delete(
        cm,
        SESSION_TOKEN_COOKIE_NAME,
        key="mr_cookie_del_session_token",
    )
    _safe_cookie_manager_delete(
        cm,
        ACTIVE_PROFILE_COOKIE_NAME,
        key="mr_cookie_del_profile",
    )


def persist_active_profile_slug_cookie(slug: str) -> None:
    """Create a DB session and store its token in the browser cookie."""
    try:
        safe = normalize_profile_slug(slug)
    except ValueError:
        return
    from pages import page_helpers as ph

    conn = ph.get_db_connection()
    token = create_session_token(conn, safe)
    persist_session_token_cookie(token)


def clear_active_profile_slug_cookie() -> None:
    """Remove session cookie and invalidate DB session token."""
    from pages import page_helpers as ph

    ph._invalidate_current_session_token()
    ph.clear_session_token_cookie()


def _invalidate_current_session_token() -> None:
    """Delete the current session token from the DB (if present in cookie)."""
    from pages import page_helpers as ph

    token = ph._read_session_token_from_cookies()
    if token is None:
        return
    conn = ph.get_db_connection()
    delete_session_token(conn, token)


def _read_session_token_from_cookies() -> str | None:
    """Read session token from CookieManager or context cookies."""
    token_ctx = peek_session_token_from_context_cookies()
    if token_ctx:
        return token_ctx
    cm = profile_cookie_manager()
    raw = cm.get(SESSION_TOKEN_COOKIE_NAME)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_session_token_from_context_cookies() -> str | None:
    """Return session token from HTTP request cookies (faster than CookieManager)."""
    try:
        raw = st.context.cookies.to_dict().get(SESSION_TOKEN_COOKIE_NAME)
    except Exception:
        return None
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_active_profile_slug_from_context_cookies() -> str | None:
    """Resolve a profile slug from the session-token cookie (context cookies)."""
    token = peek_session_token_from_context_cookies()
    if not token:
        return None
    conn = get_db_connection()
    return validate_session_token(conn, token)


def restore_active_profile_from_cookie_if_needed() -> None:
    """If server session lost the slug, restore login from session-token cookie."""
    from pages import page_helpers as ph

    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        return
    token = ph._read_session_token_from_cookies()
    if not token:
        return
    conn = ph.get_db_connection()
    slug = validate_session_token(conn, token)
    if slug is None:
        ph.clear_session_token_cookie()
        return
    data = load_user_profile(conn, slug)
    post_login_maybe_defer_profile_apply(
        st.session_state,
        profile_slug=slug,
        server_profile=data,
    )


def bootstrap_profile_session() -> None:
    """Restore profile from session-token cookie and re-hydrate (entrypoint only)."""
    restore_active_profile_from_cookie_if_needed()
    res = ensure_active_profile_hydrated(st.session_state)
    if res == ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE:
        clear_session_token_cookie()
        st.warning(
            "Gespeichertes Profil wurde nicht gefunden. "
            "Die Anmeldung wurde zurückgesetzt (Cookie entfernt).",
        )


def render_profile_sidebar() -> None:
    """Profile status and actions in the sidebar (entrypoint; runs every rerun)."""
    res = ensure_active_profile_hydrated(st.session_state)
    if res == ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE:
        clear_session_token_cookie()

    st.sidebar.markdown("### Konto")
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if active:
        st.sidebar.caption(f"Angemeldet als **{active}**")
        if st.sidebar.button(
            "Speichern",
            key="sb_prof_save",
            use_container_width=True,
        ):
            save_current_profile_to_disk()
        if st.sidebar.button(
            "Abmelden",
            key="sb_prof_logout",
            use_container_width=True,
        ):
            logout_active_profile()
            st.rerun()
    else:
        st.sidebar.caption("Kein Profil aktiv")
        if st.sidebar.button(
            "Konto",
            key="sb_prof_login",
            use_container_width=True,
        ):
            st.switch_page("pages/0c_Anmelden.py")


def render_toolbar(page_key: str) -> None:
    """Reserved hook at page top; profile controls live in the entrypoint sidebar."""
    from pages import page_helpers as ph

    ph.ensure_plattenradar_dashboard_chrome()
    _ = page_key
