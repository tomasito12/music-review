#!/usr/bin/env python3
"""Plattenradar entrypoint: ``st.navigation`` hub, profile sidebar, start page."""

from __future__ import annotations

import streamlit as st

from music_review.config import resolve_data_path
from music_review.io.reviews_jsonl import max_review_id_in_jsonl


def _welcome_corpus_stats_plain() -> str:
    """German clause from max review ``id`` in JSONL (plain text)."""
    path = resolve_data_path("data/reviews.jsonl")
    max_id = max_review_id_in_jsonl(path)
    if max_id is None:
        return "im Datenbestand dieser App sind noch keine Rezensionen erfasst"
    n_de = f"{max_id:,}".replace(",", ".")
    return f"mittlerweile sind es {n_de} Albumrezensionen"


def _welcome_css() -> None:
    st.markdown(
        """
        <style>
        .welcome-hero {
            text-align: center;
            padding: 3rem 1rem 1.5rem 1rem;
        }
        .welcome-title {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.3rem;
            color: #111827;
        }
        .welcome-subtitle {
            font-size: 1.05rem;
            color: #6b7280;
            margin-bottom: 2rem;
        }
        .welcome-body {
            max-width: 38rem;
            margin: 0 auto;
            font-size: 1rem;
            line-height: 1.7;
            color: #374151;
            text-align: left;
        }
        .welcome-body p {
            margin-bottom: 1rem;
        }
        .welcome-cta {
            text-align: center;
            margin-top: 2.5rem;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_start_page() -> None:
    """Landing copy and link to the profile step."""
    _welcome_css()

    st.markdown(
        '<div class="welcome-hero">'
        '<p class="welcome-title">Plattenradar</p>'
        '<p class="welcome-subtitle">'
        "Dein Empfehlungssystem für den plattentests.de-Kosmos"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    corpus_clause = _welcome_corpus_stats_plain()
    st.markdown(
        '<div class="welcome-body">'
        "<p>"
        "Willkommen! plattentests.de rezensiert seit 1999 "
        "Alben aus allen Ecken der Musikwelt &mdash; "
        f"{corpus_clause}. "
        "Wie viele davon würden dir gefallen, wenn du "
        "sie nur kennen würdest? Bands, die damals unter dem Radar liefen, "
        "Genres, die man nie auf dem Schirm hatte, Platten, die in keiner "
        "Playlist auftauchen. Diese App öffnet dir das gesamte Universum "
        "dieses Kosmos, damit du genau solche Alben entdecken kannst."
        "</p>"
        "<p>"
        "Die App ist zunächst zu Testzwecken für den Freundeskreis gedacht. "
        "Ein Profilname genügt, um deine Einstellungen zu speichern und "
        "später wiederzuverwenden &mdash; ganz ohne Passwort oder "
        "Registrierung."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="welcome-cta">', unsafe_allow_html=True)
    if st.button("Weiter", type="primary", width="stretch", key="start_page_weiter"):
        st.switch_page("pages/0_Profil.py")
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar",
        page_icon=None,
        layout="centered",
    )

    from pages.page_helpers import bootstrap_profile_session, render_profile_sidebar

    bootstrap_profile_session()
    render_profile_sidebar()

    pages = [
        st.Page(render_start_page, title="Start", default=True),
        st.Page("pages/0_Profil.py", title="Profil"),
        st.Page("pages/0b_Einstieg.py", title="Einstieg"),
        st.Page("pages/1_Community_Auswahl.py", title="Genre / Stil"),
        st.Page("pages/4_Text_Flow.py", title="Freitext"),
        st.Page("pages/5_Filter_Flow.py", title="Filter"),
        st.Page("pages/6_Recommendations_Flow.py", title="Empfehlungen"),
        st.Page("pages/8_Neueste_Rezensionen.py", title="Neueste Rezensionen"),
        st.Page("pages/7_Freitext_Qualitaet.py", title="Freitext-Qualität"),
        st.Page("pages/9_Spotify_Playlists.py", title="Spotify"),
    ]
    st.navigation(pages).run()


if __name__ == "__main__":
    main()
