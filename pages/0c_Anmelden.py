"""Sign-in for guests and account management when logged in (German UI)."""

from __future__ import annotations

import streamlit as st
from pages.konto_session_panel import render_logged_in_konto_panel
from pages.page_helpers import (
    ACTIVE_PROFILE_SESSION_KEY,
    WIZARD_ACCOUNT_SAVE_INTENT_KEY,
    persist_active_profile_from_session,
    session_taste_setup_complete,
)
from pages.profil_auth_actions import run_sign_in

from music_review.dashboard.streamlit_branding import (
    ensure_plattenradar_dashboard_chrome,
)
from music_review.dashboard.user_profile_store import (
    LOGIN_GUEST_SESSION_PINNED_KEY,
    LOGIN_PROFILE_MERGE_PENDING_KEY,
    apply_profile_to_session,
)


def _konto_logged_in_css() -> None:
    st.markdown(
        """
        <style>
        .anmelden-konto-hero {
            text-align: center;
            padding: 1.25rem 1rem 0.75rem 1rem;
        }
        .anmelden-konto-title {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.35rem;
            color: #111827;
        }
        .anmelden-konto-subtitle {
            font-size: 1rem;
            color: #6b7280;
            margin-bottom: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _anmelden_css() -> None:
    st.markdown(
        """
        <style>
        .anmelden-hero {
            text-align: center;
            padding: 1.25rem 1rem 0.75rem 1rem;
        }
        .anmelden-title {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.35rem;
            color: #111827;
        }
        .anmelden-card {
            max-width: 22rem;
            margin: 0 auto 1.5rem auto;
        }
        .anmelden-register {
            text-align: center;
            margin-top: 1.25rem;
            font-size: 0.95rem;
            color: #4b5563;
        }
        .anmelden-skip-login {
            text-align: center;
            margin-top: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


KEY_ANMELDEN_USERNAME = "anmelden_page_username"
KEY_ANMELDEN_PASSWORD = "anmelden_page_password"


def main() -> None:
    ensure_plattenradar_dashboard_chrome()
    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    merge_pending = st.session_state.get(LOGIN_PROFILE_MERGE_PENDING_KEY)
    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY) and merge_pending:
        _konto_logged_in_css()
        st.markdown(
            '<div class="anmelden-konto-hero">'
            '<p class="anmelden-konto-title">Profil und Sitzung</p>'
            '<p class="anmelden-konto-subtitle">'
            "Du hast dich angemeldet, während in dieser Sitzung bereits "
            "Musikpräferenzen, Filter oder Gewichte eingestellt waren."
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "Wähle, ob dein **gespeichertes Nutzerprofil** mit der aktuellen Sitzung "
            "abgeglichen werden soll, die Sitzung unverändert bleiben soll "
            "(ohne Speichern auf dem Profil), oder ob die **gespeicherten** "
            "Einstellungen geladen und die Sitzung damit ersetzt werden soll."
        )
        col_overwrite, col_keep_session, col_load_server = st.columns(3)
        with col_overwrite:
            if st.button(
                "Profil mit aktueller Auswahl überschreiben",
                type="primary",
                width="stretch",
                key="login_merge_overwrite",
            ):
                persist_active_profile_from_session()
                st.session_state.pop(LOGIN_PROFILE_MERGE_PENDING_KEY, None)
                st.session_state.pop(LOGIN_GUEST_SESSION_PINNED_KEY, None)
                st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
                st.rerun()
        with col_keep_session:
            if st.button(
                "Profil nicht ändern, Sitzung behalten",
                width="stretch",
                key="login_merge_keep_session",
            ):
                st.session_state.pop(LOGIN_PROFILE_MERGE_PENDING_KEY, None)
                st.session_state[LOGIN_GUEST_SESSION_PINNED_KEY] = True
                st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
                st.rerun()
        with col_load_server:
            if st.button(
                "Gespeichertes Profil laden",
                width="stretch",
                key="login_merge_load_server",
            ):
                server = merge_pending.get("server_profile")
                if isinstance(server, dict) and server:
                    apply_profile_to_session(st.session_state, server)
                st.session_state.pop(LOGIN_PROFILE_MERGE_PENDING_KEY, None)
                st.session_state.pop(LOGIN_GUEST_SESSION_PINNED_KEY, None)
                st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
                st.rerun()
        return

    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        _konto_logged_in_css()
        st.markdown(
            '<div class="anmelden-konto-hero">'
            '<p class="anmelden-konto-title">Konto</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        render_logged_in_konto_panel()
        return

    _anmelden_css()

    st.markdown(
        '<div class="anmelden-hero"><p class="anmelden-title">Anmelden</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="anmelden-card">', unsafe_allow_html=True)
    with st.form("anmelden_form", clear_on_submit=False):
        username = st.text_input(
            "Benutzername",
            key=KEY_ANMELDEN_USERNAME,
        )
        password = st.text_input(
            "Passwort",
            type="password",
            key=KEY_ANMELDEN_PASSWORD,
        )
        submitted = st.form_submit_button(
            "Anmelden",
            type="primary",
            width="stretch",
        )
    if submitted:
        run_sign_in(username, password)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<p class="anmelden-register">Noch kein Konto?</p>',
        unsafe_allow_html=True,
    )
    if st.button(
        "Registrieren",
        key="anmelden_to_register",
        width="stretch",
    ):
        st.switch_page("pages/0d_Nutzerkonto_anlegen.py")

    st.markdown('<div class="anmelden-skip-login">', unsafe_allow_html=True)
    if st.button(
        "Weiter ohne Login",
        key="anmelden_skip_login",
        width="stretch",
    ):
        st.session_state.pop(WIZARD_ACCOUNT_SAVE_INTENT_KEY, None)
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
