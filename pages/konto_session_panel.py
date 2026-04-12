"""Logged-in account UI: status, password change, taste reset, continue (Streamlit)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    logout_active_profile,
    reset_taste_preferences,
    session_taste_setup_complete,
)

from music_review.dashboard.user_db import (
    authenticate_user,
    change_password,
    get_connection,
)
from music_review.dashboard.user_profile_store import ACTIVE_PROFILE_SESSION_KEY

KEY_KONTO_SIGN_OUT = "konto_panel_sign_out"
KEY_CHANGE_PW_OLD = "konto_panel_change_pw_old"
KEY_CHANGE_PW_NEW = "konto_panel_change_pw_new"
KEY_CHANGE_PW_CONFIRM = "konto_panel_change_pw_confirm"
KEY_RESET_CONFIRM = "konto_panel_reset_confirm"
KEY_RESET_RUN = "konto_panel_reset_run"
KEY_WEITER = "konto_panel_weiter"


def _render_change_password() -> None:
    """Expander to change the password of the logged-in user."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        return
    with st.expander("Passwort ändern"):
        old_pw = st.text_input(
            "Aktuelles Passwort",
            type="password",
            key=KEY_CHANGE_PW_OLD,
        )
        new_pw = st.text_input(
            "Neues Passwort",
            type="password",
            key=KEY_CHANGE_PW_NEW,
        )
        new_pw_confirm = st.text_input(
            "Neues Passwort bestätigen",
            type="password",
            key=KEY_CHANGE_PW_CONFIRM,
        )
        if st.button("Passwort ändern", key="konto_panel_change_pw_btn"):
            if not old_pw:
                st.error("Bitte gib dein aktuelles Passwort ein.")
                return
            conn = get_connection()
            if not authenticate_user(conn, active, old_pw):
                st.error("Aktuelles Passwort ist falsch.")
                return
            if not new_pw or len(new_pw) < 4:
                st.error("Neues Passwort muss mindestens 4 Zeichen haben.")
                return
            if new_pw != new_pw_confirm:
                st.error("Neue Passwörter stimmen nicht überein.")
                return
            change_password(conn, active, new_pw)
            st.success("Passwort wurde geändert.")


def _render_active_profile() -> None:
    """Show status and logout for the active profile."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        return

    with st.container(border=True):
        st.success(f"Angemeldet als **{active}**")
        if st.button(
            "Abmelden",
            key=KEY_KONTO_SIGN_OUT,
            width="stretch",
        ):
            logout_active_profile()
            st.rerun()

    _render_change_password()


def render_logged_in_konto_panel() -> None:
    """Full account panel: reset taste, profile status, password, continue."""
    st.markdown(
        """
        <style>
        .konto-panel-cta {
            text-align: center;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Filter und Stile zurücksetzen"):
        st.markdown(
            "Leert Stil- und Filtereinstellungen in dieser Sitzung. "
            "Dein gespeichertes Profil bleibt unverändert, bis du "
            "in der Seitenleiste **Speichern** wählst."
        )
        confirm = st.checkbox(
            "Ja, Filter und Stile zurücksetzen.",
            key=KEY_RESET_CONFIRM,
        )
        if st.button(
            "Filter und Stile zurücksetzen",
            disabled=not confirm,
            key=KEY_RESET_RUN,
        ):
            reset_taste_preferences()
            st.switch_page("pages/0b_Einstieg.py")

    _render_active_profile()

    st.markdown('<div class="konto-panel-cta">', unsafe_allow_html=True)
    if st.button("Weiter", type="primary", width="stretch", key=KEY_WEITER):
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)
