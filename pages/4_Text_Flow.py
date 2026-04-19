from __future__ import annotations

import streamlit as st
from pages.page_helpers import render_toolbar


def _ensure_session_state() -> None:
    if "free_text_query" not in st.session_state:
        st.session_state["free_text_query"] = ""


def main() -> None:
    _ensure_session_state()
    render_toolbar("text_flow")

    st.title("Stimmung / Freitext-Eingabe")
    st.markdown(
        "Beschreibe hier, wonach du suchst - Stimmung, Klangbilder, Nuancen.\n\n"
        "Beispiele:\n"
        "- „melancholisch, herbstlich“\n"
        "- „Gitarren-Gewitter“\n"
        "- „Grunge mit Melodien“",
    )

    text = st.text_area(
        "Freitext",
        value=st.session_state.get("free_text_query", ""),
        placeholder='z. B. "melancholisch, herbstlich"',
        height=140,
    )
    st.session_state["free_text_query"] = text

    st.info(
        "Die Eingabe ist aktuell nur im Session State gespeichert und "
        "wird im nächsten Schritt für die Filterung und Empfehlungen verwendet.",
    )

    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_back:
        st.page_link(
            "pages/0b_Einstieg.py",
            label="Zur Startseite",
            use_container_width=True,
        )
    with col_next:
        st.page_link(
            "pages/5_Filter_Flow.py",
            label="Weiter",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
