"""Legacy path: account and sign-in now live on the Konto page (0c)."""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.switch_page("pages/0c_Anmelden.py")


if __name__ == "__main__":
    main()
