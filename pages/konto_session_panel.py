"""Logged-in account UI: status and continue (Streamlit)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    logout_active_profile,
    session_taste_setup_complete,
)

from music_review.dashboard.user_profile_store import ACTIVE_PROFILE_SESSION_KEY

KEY_KONTO_SIGN_OUT = "konto_panel_sign_out"
KEY_WEITER = "konto_panel_weiter"


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


def render_logged_in_konto_panel() -> None:
    """Account panel: profile status and continue."""
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
    _render_active_profile()

    st.markdown('<div class="konto-panel-cta">', unsafe_allow_html=True)
    if st.button("Weiter", type="primary", width="stretch", key=KEY_WEITER):
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)
