from __future__ import annotations

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths


def _ensure_session_state() -> None:
    if "free_text_query" not in st.session_state:
        st.session_state["free_text_query"] = ""


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Freitext",
        page_icon="🎵",
        layout="wide",
    )

    _ensure_session_state()

    st.title("✏️ Stimmung / Freitext-Eingabe")
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
        if st.button("Zur Startseite"):
            st.switch_page("streamlit_app.py")
    with col_next:
        if st.button("Weiter"):
            st.switch_page("pages/5_Filter_Flow.py")


if __name__ == "__main__":
    main()
