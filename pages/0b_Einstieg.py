"""Flow-Auswahl: Genre, Artist oder kombiniert."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import render_toolbar


def _einstieg_css() -> None:
    st.markdown(
        """
        <style>
        .einstieg-title {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.15rem;
            color: #111827;
        }
        .einstieg-desc {
            color: #6b7280;
            font-size: 0.92rem;
            margin-bottom: 1.3rem;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar -- Einstieg",
        page_icon=None,
        layout="wide",
    )

    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    render_toolbar("einstieg")
    _einstieg_css()

    st.markdown(
        '<p class="einstieg-title">Wie möchtest du starten?</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="einstieg-desc">'
        "Wähle einen Einstieg &mdash; du kannst später jederzeit "
        "zurück zu dieser Seite wechseln."
        "</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1, st.container(border=True):
        st.subheader("Genres / Moods")
        st.caption(
            "Starte mit Communities, Genres und Moods. "
            "Ideal, wenn du eher eine Stimmung als konkrete "
            "Künstler im Kopf hast.",
        )
        if st.button(
            "Diesen Weg wählen",
            key="start_genre_flow",
            use_container_width=True,
        ):
            st.session_state["flow_mode"] = "genres"
            st.switch_page("pages/2_Genre_Flow.py")

    with col2, st.container(border=True):
        st.subheader("Artists")
        st.caption(
            "Starte mit Künstlern, die du magst, und entdecke "
            "ähnliche Alben über das Community- und RAG-System.",
        )
        if st.button(
            "Diesen Weg wählen",
            key="start_artist_flow",
            use_container_width=True,
        ):
            st.session_state["flow_mode"] = "artists"
            st.switch_page("pages/1_Artist_Flow.py")

    with col3, st.container(border=True):
        st.subheader("Beides kombinieren")
        st.caption(
            "Kombiniere Artist- und Genre/Mood-Signale zu einem "
            "mehrstufigen Recommender-Prozess.",
        )
        if st.button(
            "Diesen Weg wählen",
            key="start_combined_flow",
            use_container_width=True,
        ):
            st.session_state["flow_mode"] = "combined"
            st.switch_page("pages/1_Artist_Flow.py")

    st.markdown("---")
    if st.button("Zurück zum Profil"):
        st.switch_page("pages/0_Profil.py")


if __name__ == "__main__":
    main()
