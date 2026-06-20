"""Focused account registration page (German UI)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    ACTIVE_PROFILE_SESSION_KEY,
    clear_session_token_cookie,
    session_taste_setup_complete,
)
from pages.profil_auth_actions import run_register

from music_review.dashboard.streamlit_branding import (
    ensure_plattenradar_dashboard_chrome,
)

KEY_NUTZERKONTO_USERNAME = "nutzerkonto_page_username"
KEY_NUTZERKONTO_PASSWORD = "nutzerkonto_page_password"
KEY_NUTZERKONTO_PASSWORD_CONFIRM = "nutzerkonto_page_password_confirm"


def _nutzerkonto_css() -> None:
    st.markdown(
        """
        <style>
        .nutzerkonto-hero {
            text-align: center;
            padding: 1.25rem 1rem 0.75rem 1rem;
        }
        .nutzerkonto-title {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 1rem;
            color: #111827;
        }
        .nutzerkonto-intro {
            max-width: 28rem;
            margin: 0 auto 1.5rem auto;
            text-align: center;
            font-size: 1rem;
            line-height: 1.65;
            color: #374151;
        }
        .nutzerkonto-form {
            max-width: 22rem;
            margin: 0 auto 1rem auto;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    ensure_plattenradar_dashboard_chrome()
    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")

    _nutzerkonto_css()

    st.markdown(
        '<div class="nutzerkonto-hero">'
        '<p class="nutzerkonto-title">Nutzerkonto anlegen</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="nutzerkonto-intro">'
        "Deine Musikvorlieben werden gespeichert und mit einem Passwort "
        "geschützt. Beim nächsten Besuch kannst du direkt weitermachen."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="nutzerkonto-form">', unsafe_allow_html=True)
    with st.form("nutzerkonto_form", clear_on_submit=False):
        username = st.text_input(
            "Bitte wähle einen Benutzernamen",
            key=KEY_NUTZERKONTO_USERNAME,
        )
        password = st.text_input(
            "Passwort",
            type="password",
            key=KEY_NUTZERKONTO_PASSWORD,
        )
        password_confirm = st.text_input(
            "Passwort bestätigen",
            type="password",
            key=KEY_NUTZERKONTO_PASSWORD_CONFIRM,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            submitted = st.form_submit_button(
                "Registrierung abschließen",
                type="primary",
                width="stretch",
            )
        with col_b:
            skip = st.form_submit_button(
                "Ohne Registrierung weiter",
                width="stretch",
            )

    if submitted:
        run_register(username, password, password_confirm)
    elif skip:
        st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
        clear_session_token_cookie()
        st.session_state["flow_mode"] = None
        st.switch_page("pages/0b_Einstieg.py")

    st.markdown("</div>", unsafe_allow_html=True)

    _pad_l, col_login, _pad_r = st.columns([1, 5, 1])
    with col_login:
        login_hint = "Du hast bereits einen Nutzernamen? Dann melde dich hier an."
        if st.button(
            login_hint,
            key="nutzerkonto_to_login",
            type="tertiary",
            width="stretch",
        ):
            st.switch_page("pages/0c_Anmelden.py")


if __name__ == "__main__":
    main()
