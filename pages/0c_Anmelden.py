"""Dedicated sign-in page (German UI)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    ACTIVE_PROFILE_SESSION_KEY,
    session_taste_setup_complete,
)
from pages.profil_auth_actions import run_sign_in


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
    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")

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
        st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
