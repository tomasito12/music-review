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
from music_review.dashboard.streamlit_branding import (
    ensure_plattenradar_dashboard_chrome,
    read_processed_dashboard_logo_bytes,
    welcome_start_title_inner_html,
)
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
        /* Start page: center the card in the viewport; frame hugs content height. */
        section[data-testid="stMain"]:has(.welcome-hero) {
            min-height: calc(100dvh - 4rem) !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            padding: 1.25rem 0.75rem 2rem 0.75rem !important;
            overflow: visible !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stMain"]:has(.welcome-hero) .block-container {
            width: 100% !important;
            max-width: 38rem !important;
            margin: 0 auto !important;
            padding: 1.35rem 1.25rem 1.5rem 1.25rem !important;
            border: 2px solid #dc2626 !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 22px rgba(185, 28, 28, 0.12) !important;
            overflow: visible !important;
            box-sizing: border-box !important;
        }
        section[data-testid="stMain"]:has(.welcome-hero)
            [data-testid="stMarkdownContainer"] {
            overflow: visible !important;
        }
        div[data-testid="stMarkdownContainer"]:has(.welcome-body) {
            text-align: center !important;
        }
        .welcome-hero {
            text-align: center;
            padding: 0.35rem 0.5rem 0.85rem 0.5rem;
            margin-bottom: 1.15rem;
            overflow: visible;
        }
        /* Do not use ``.welcome-hero p`` alone: it beats ``.welcome-subtitle`` and
           zeros out the subtitle's top margin. Only reset logo / title paragraphs. */
        .welcome-hero p.welcome-logo,
        .welcome-hero p.welcome-title {
            margin-block: 0 !important;
        }
        .welcome-logo {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 0;
        }
        .welcome-title-img {
            display: block;
            margin: 0 auto;
            max-width: min(100%, 22rem);
            max-height: 8.75rem;
            width: auto;
            height: auto;
            object-fit: contain;
            vertical-align: bottom;
            image-rendering: auto;
        }
        .welcome-title {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            line-height: 1.15;
            margin: 0 !important;
            padding-top: 0.08em;
            color: #111827;
            overflow: visible;
        }
        .welcome-hero p.welcome-subtitle {
            font-size: 1.05rem;
            color: #6b7280;
            margin: 2.25rem 0 0 0 !important;
            padding-top: 0 !important;
            line-height: 1.35;
        }
        .welcome-body {
            max-width: 38rem;
            margin: 0 auto 1.35rem auto;
            font-size: 1rem;
            line-height: 1.7;
            color: #374151;
            text-align: center;
        }
        .welcome-body p {
            margin-bottom: 1rem;
        }
        .welcome-cta {
            text-align: center;
            margin-top: 0.85rem;
            margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_start_page() -> None:
    """Landing copy and context-sensitive next steps (returning vs new)."""
    ensure_plattenradar_dashboard_chrome()
    _welcome_css()

    title_inner = welcome_start_title_inner_html(read_processed_dashboard_logo_bytes())
    st.markdown(
        '<div class="welcome-hero">'
        f"{title_inner}"
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
            if st.button("Anderes Konto", width="stretch", key="start_other_profile"):
                logout_active_profile()
                st.switch_page("pages/0c_Anmelden.py")
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
                "Zum Konto",
                width="stretch",
                key="start_to_profile_incomplete",
            ):
                st.switch_page("pages/0c_Anmelden.py")
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
        if st.button(
            "Konto anlegen",
            width="stretch",
            key="start_guest_profile",
        ):
            st.switch_page("pages/0d_Nutzerkonto_anlegen.py")
    else:
        col_discover, col_login, col_register = st.columns([2, 1, 1])
        with col_discover:
            if st.button(
                "Entdecken",
                type="primary",
                width="stretch",
                key="start_entdecken_step1",
            ):
                st.switch_page("pages/0b_Einstieg.py")
        with col_login:
            if st.button("Einloggen", width="stretch", key="start_einloggen"):
                st.switch_page("pages/0c_Anmelden.py")
        with col_register:
            if st.button(
                "Konto anlegen",
                width="stretch",
                key="start_konto_anlegen",
            ):
                st.switch_page("pages/0d_Nutzerkonto_anlegen.py")

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
        st.Page(
            "pages/0c_Anmelden.py",
            title="Konto",
            url_path="konto",
        ),
        st.Page(
            "pages/0d_Nutzerkonto_anlegen.py",
            title="Konto anlegen",
            url_path="konto_anlegen",
        ),
        st.Page("pages/0b_Einstieg.py", title="Einstieg"),
        st.Page("pages/1_Community_Auswahl.py", title="Genre / Stil"),
        st.Page("pages/5_Filter_Flow.py", title="Filter"),
        # Hub after the three setup steps; shows a guard until setup is complete.
        st.Page("pages/2_Entdecken.py", title="Entdecken"),
        # OAuth return can open a fresh session without taste setup; page must exist.
        _spotify_nav_page(),
    ]
    full_app = [
        st.Page(render_start_page, title="Start", default=True),
        st.Page(
            "pages/0c_Anmelden.py",
            title="Konto",
            url_path="konto",
        ),
        st.Page(
            "pages/0d_Nutzerkonto_anlegen.py",
            title="Konto anlegen",
            url_path="konto_anlegen",
        ),
        st.Page("pages/0b_Einstieg.py", title="Einstieg"),
        st.Page("pages/1_Community_Auswahl.py", title="Genre / Stil"),
        st.Page("pages/5_Filter_Flow.py", title="Filter"),
        st.Page("pages/2_Entdecken.py", title="Entdecken"),
        st.Page("pages/4_Text_Flow.py", title="Freitext"),
        st.Page("pages/6_Recommendations_Flow.py", title="Empfehlungen"),
        st.Page("pages/8_Neueste_Rezensionen.py", title="Neueste Rezensionen"),
        st.Page("pages/7_Freitext_Qualitaet.py", title="Freitext-Qualität"),
        st.Page(
            "pages/3_Streaming_Verbindungen.py",
            title="Streaming-Verbindungen",
        ),
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
