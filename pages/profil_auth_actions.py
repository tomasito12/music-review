"""Shared profile sign-in and guest-flow navigation state (Streamlit)."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import streamlit as st
from pages.page_helpers import persist_active_profile_slug_cookie

from music_review.dashboard.user_db import (
    authenticate_user,
    get_connection,
    user_exists,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    load_profile,
    normalize_profile_slug,
)

PROFIL_GUEST_FLOW_PENDING_KEY = "profil_guest_flow_pending"
PROFIL_GUEST_FLOW_RADIO_KEY = "profil_guest_flow_radio"

GUEST_FLOW_LOGIN = "Anmelden"
GUEST_FLOW_REGISTER = "Registrieren"
GUEST_FLOW_SKIP = "Ohne Profil weiter"
GUEST_FLOW_OPTIONS: tuple[str, ...] = (
    GUEST_FLOW_LOGIN,
    GUEST_FLOW_REGISTER,
    GUEST_FLOW_SKIP,
)


def apply_pending_guest_flow_to_radio_state(state: MutableMapping[str, Any]) -> None:
    """Copy pending guest-flow choice into the radio widget session key."""
    pending = state.pop(PROFIL_GUEST_FLOW_PENDING_KEY, None)
    if pending in GUEST_FLOW_OPTIONS:
        state[PROFIL_GUEST_FLOW_RADIO_KEY] = pending


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
