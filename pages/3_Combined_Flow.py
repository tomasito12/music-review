from __future__ import annotations

import streamlit as st
from pages.page_helpers import render_toolbar


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Kombinierter Flow",
        page_icon=None,
        layout="wide",
    )
    render_toolbar("combined_flow")

    st.title("Kombinierter Artist- & Genre-Flow")
    st.markdown(
        "Diese Seite ist ein Platzhalter für den kombinierten Flow.\n\n"
        "- Hier kombinierst du später Artist- und Genre/Community-Signale.\n"
        "- Du kannst jederzeit über die Sidebar zurück zur Startseite wechseln.",
    )

    if st.button("Zur Startseite"):
        st.switch_page("pages/0b_Einstieg.py")


if __name__ == "__main__":
    main()
