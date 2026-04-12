"""Shared profile sign-in and registration actions (Streamlit)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    build_session_profile_payload,
    persist_active_profile_slug_cookie,
)

from music_review.dashboard.user_db import (
    authenticate_user,
    create_user,
    get_connection,
    user_exists,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    load_profile,
    normalize_profile_slug,
    save_profile,
)

REGISTER_MIN_PASSWORD_LENGTH = 4


def run_sign_in(name_raw: str, password: str) -> None:
    """Validate input, authenticate, hydrate session, persist cookie, then rerun."""
    if not (name_raw or "").strip():
        st.error("Bitte gib einen Profilnamen ein.")
        return
    try:
        safe = normalize_profile_slug(name_raw)
    except ValueError as err:
        st.error(str(err))
        return
    if not password:
        st.error("Bitte gib dein Passwort ein.")
        return
    conn = get_connection()
    if not user_exists(conn, safe):
        st.error("Profil nicht gefunden.")
        return
    if not authenticate_user(conn, safe, password):
        st.error("Passwort ist falsch.")
        return
    data = load_profile(None, safe)  # type: ignore[arg-type]
    if data is not None:
        apply_profile_to_session(st.session_state, data)
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = safe
    persist_active_profile_slug_cookie(safe)
    st.rerun()


def run_register(name_raw: str, password: str, password_confirm: str) -> None:
    """Create a new account, hydrate session, persist cookie, go to step 1 of 4."""
    if not (name_raw or "").strip():
        st.error("Bitte gib einen Benutzernamen ein.")
        return
    try:
        slug = normalize_profile_slug(name_raw)
    except ValueError as err:
        st.error(str(err))
        return
    if not password or len(password) < REGISTER_MIN_PASSWORD_LENGTH:
        n = REGISTER_MIN_PASSWORD_LENGTH
        st.error(f"Passwort muss mindestens {n} Zeichen lang sein.")
        return
    if password != password_confirm:
        st.error("Passwörter stimmen nicht überein.")
        return
    conn = get_connection()
    if not create_user(conn, slug, password):
        st.error(
            "Ein Profil mit diesem Namen existiert bereits. "
            "Wenn es dein Profil ist, melde dich unter "
            "\u201eAnmelden\u201c mit demselben Namen an. "
            "Andernfalls wähle einen anderen Namen.",
        )
        return
    payload = build_session_profile_payload(profile_slug=slug)
    save_profile(None, slug, payload)  # type: ignore[arg-type]
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug
    persist_active_profile_slug_cookie(slug)
    apply_profile_to_session(st.session_state, payload)
    st.switch_page("pages/0b_Einstieg.py")
