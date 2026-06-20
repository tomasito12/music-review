"""Legacy path: account and sign-in now live on the Konto page (0c)."""

from __future__ import annotations

import streamlit as st

from music_review.dashboard.streamlit_branding import (
    ensure_plattenradar_dashboard_chrome,
)


def main() -> None:
    ensure_plattenradar_dashboard_chrome()
    st.switch_page("pages/0c_Anmelden.py")


if __name__ == "__main__":
    main()
