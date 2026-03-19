#!/usr/bin/env python3
"""Start page for the multi-step music recommendation flow."""

from __future__ import annotations

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Start",
        page_icon="🎵",
        layout="wide",
    )

    st.title("🎵 Music Review Recommender")
    st.markdown(
        "**Wie möchtest du zu deinen Empfehlungen kommen?** "
        "Wähle einen Einstieg - du kannst später jederzeit zurück zur "
        "Startseite wechseln.",
    )

    st.markdown("---")

    # Flow-Modus zurücksetzen, wenn man die Startseite besucht
    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Musik-Stile / Genres / Moods")
        st.caption(
            "Starte mit Communities, Genres und Moods. "
            "Ideal, wenn du eher eine Stimmung als konkrete Künstler im Kopf hast.",
        )
        if st.button("Diesen Weg wählen", key="start_genre_flow"):
            st.session_state["flow_mode"] = "genres"
            st.switch_page("pages/2_Genre_Flow.py")

    with col2:
        st.subheader("Artists")
        st.caption(
            "Starte mit Künstlern, die du magst, und entdecke ähnliche Alben "
            "über das Community- und RAG-System.",
        )
        if st.button("Diesen Weg wählen", key="start_artist_flow"):
            st.session_state["flow_mode"] = "artists"
            st.switch_page("pages/1_Artist_Flow.py")

    with col3:
        st.subheader("Beides kombinieren")
        st.caption(
            "Kombiniere Artist- und Genre/Mood-Signale zu einem mehrstufigen "
            "Recommender-Prozess.",
        )
        if st.button("Diesen Weg wählen", key="start_combined_flow"):
            st.session_state["flow_mode"] = "combined"
            st.switch_page("pages/1_Artist_Flow.py")

    st.markdown("---")
    st.caption(
        "Hinweis: Die bisherige Dashboard-Ansicht ist unter "
        "`archive/streamlit_app_legacy.py` weiterhin verfügbar.",
    )


if __name__ == "__main__":
    main()
