#!/usr/bin/env python3
"""Welcome / landing page for the Plattenradar."""

from __future__ import annotations

import streamlit as st


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


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar",
        page_icon=None,
        layout="centered",
    )

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

    st.markdown(
        '<div class="welcome-body">'
        "<p>"
        "Willkommen! <strong>plattentests.de</strong> rezensiert seit 1999 "
        "Alben aus allen Ecken der Musikwelt &mdash; mittlerweile sind es "
        "über 21.000 Stück. Wie viele davon würden dir gefallen, wenn du "
        "sie nur kennen würdest? Bands, die damals unter dem Radar liefen, "
        "Genres, die man nie auf dem Schirm hatte, Platten, die in keiner "
        "Playlist auftauchen. Diese App öffnet dir das gesamte Universum "
        "dieses Kosmos, damit du genau solche Alben entdecken kannst."
        "</p>"
        "<p>"
        "Die Grundlage bilden sämtliche Rezensionen von plattentests.de, "
        "angereichert mit Metadaten aus MusicBrainz und aufbereitet durch ein "
        "AI-basiertes Empfehlungssystem. Du kannst über "
        "<strong>Genres und Stimmungen</strong>, über "
        "<strong>Künstler</strong> oder über beides kombiniert einsteigen. "
        "Zusätzlich steht dir eine Freitext-Suche zur Verfügung, mit der du "
        "beschreiben kannst, wonach dir gerade ist &mdash; das System findet "
        "passende Alben per semantischer Ähnlichkeit."
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
    if st.button("Weiter", type="primary", use_container_width=True):
        st.switch_page("pages/0_Profil.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
