#!/usr/bin/env python3
"""Plattenradar entrypoint: ``st.navigation`` hub, profile sidebar, start page."""

from __future__ import annotations

from typing import Any

import streamlit as st
from pages.neueste_reviews_pool import configure_spotify_playlist_logging_from_env
from pages.page_helpers import (
    ACTIVE_PROFILE_SESSION_KEY,
    bootstrap_profile_session,
    logout_active_profile,
    render_profile_sidebar,
    session_taste_setup_complete,
)

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
    """Landing copy and context-sensitive next steps (returning vs new)."""
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

    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    complete = session_taste_setup_complete()

    st.markdown('<div class="welcome-cta">', unsafe_allow_html=True)
    if active and complete:
        label = f"Weiter als {active}"
        if st.button(label, type="primary", width="stretch", key="start_resume_hub"):
            st.switch_page("pages/2_Entdecken.py")
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Anderes Profil", width="stretch", key="start_other_profile"):
                st.switch_page("pages/0_Profil.py")
        with s2:
            if st.button("Abmelden", width="stretch", key="start_logout"):
                logout_active_profile()
                st.rerun()
    elif active and not complete:
        if st.button(
            "Filter und Stile einrichten",
            type="primary",
            width="stretch",
            key="start_setup_taste",
        ):
            st.switch_page("pages/0b_Einstieg.py")
        inc1, inc2 = st.columns(2)
        with inc1:
            if st.button(
                "Zum Profil",
                width="stretch",
                key="start_to_profile_incomplete",
            ):
                st.switch_page("pages/0_Profil.py")
        with inc2:
            if st.button("Abmelden", width="stretch", key="start_logout_incomplete"):
                logout_active_profile()
                st.rerun()
    elif not active and complete:
        if st.button(
            "Entdecken",
            type="primary",
            width="stretch",
            key="start_guest_hub",
        ):
            st.switch_page("pages/2_Entdecken.py")
        st.caption(
            "Deine Filter und Stile sind eingerichtet. "
            "Im nächsten Schritt wählst du, was du entdecken möchtest."
        )
        if st.button(
            "Profil anlegen",
            width="stretch",
            key="start_guest_profile",
        ):
            st.switch_page("pages/0_Profil.py")
        st.caption("Ohne Profil bleiben Einstellungen nur in diesem Tab gültig.")
    else:
        if st.button(
            "Neu starten",
            type="primary",
            width="stretch",
            key="start_new_wizard",
        ):
            st.switch_page("pages/0b_Einstieg.py")
        if st.button("Profil laden", width="stretch", key="start_load_profile"):
            st.switch_page("pages/0_Profil.py")

    with st.expander("Was ist ein Profil?"):
        st.markdown(
            "Ein Profil ist nur ein Name auf diesem Gerät. Damit kannst du "
            "deine Genre-Auswahl und Filter speichern und beim nächsten Besuch "
            "weitermachen. Ohne Profil bleibt alles nur im offenen Tab gültig."
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _spotify_nav_page() -> Any:
    """Stable OAuth redirect path (must match ``SPOTIFY_REDIRECT_URI`` path segment)."""
    return st.Page(
        "pages/9_Spotify_Playlists.py",
        title="Spotify",
        url_path="spotify_playlists",
    )


def _navigation_pages() -> list[Any]:
    """Full app after taste setup; reduced sidebar during onboarding."""
    onboarding = [
        st.Page(render_start_page, title="Start", default=True),
        st.Page("pages/0_Profil.py", title="Profil"),
        st.Page("pages/0b_Einstieg.py", title="Einstieg"),
        st.Page("pages/1_Community_Auswahl.py", title="Genre / Stil"),
        st.Page("pages/5_Filter_Flow.py", title="Filter"),
        # Reachable after Schritt 3 (page_link); shows a guard until setup is complete.
        st.Page("pages/2_Entdecken.py", title="Entdecken"),
        # OAuth return can open a fresh session without taste setup; page must exist.
        _spotify_nav_page(),
    ]
    full_app = [
        st.Page(render_start_page, title="Start", default=True),
        st.Page("pages/0_Profil.py", title="Profil"),
        st.Page("pages/0b_Einstieg.py", title="Einstieg"),
        st.Page("pages/1_Community_Auswahl.py", title="Genre / Stil"),
        st.Page("pages/5_Filter_Flow.py", title="Filter"),
        st.Page("pages/2_Entdecken.py", title="Entdecken"),
        st.Page("pages/4_Text_Flow.py", title="Freitext"),
        st.Page("pages/6_Recommendations_Flow.py", title="Empfehlungen"),
        st.Page("pages/8_Neueste_Rezensionen.py", title="Neueste Rezensionen"),
        st.Page("pages/7_Freitext_Qualitaet.py", title="Freitext-Qualität"),
        _spotify_nav_page(),
    ]
    if session_taste_setup_complete():
        return full_app
    return onboarding


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar",
        page_icon=None,
        layout="centered",
    )

    configure_spotify_playlist_logging_from_env()
    bootstrap_profile_session()
    render_profile_sidebar()

    st.navigation(_navigation_pages()).run()


if __name__ == "__main__":
    main()
