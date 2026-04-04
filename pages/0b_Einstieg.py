"""Grobe Stilrichtungen auswählen (erster Schritt vor der feinen Musikauswahl)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import load_broad_categories_res_10, render_toolbar


def _einstieg_css() -> None:
    """Match Schritt-2-Seite: zentriert, rote Eyebrow, Hint-Box."""
    st.markdown(
        """
        <style>
        .einstieg-hero {
            text-align: center;
            padding: 1.1rem 0.75rem 0.35rem 0.75rem;
        }
        .einstieg-eyebrow {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.4rem;
        }
        .einstieg-title {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
            color: #111827;
        }
        .einstieg-desc {
            max-width: 34rem;
            margin: 0 auto 0.85rem auto;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.58;
            text-align: center;
        }
        .einstieg-hint {
            max-width: 34rem;
            margin: 0 auto 1.1rem auto;
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 0.8rem 1rem;
            font-size: 0.86rem;
            color: #44403c;
            line-height: 1.55;
            text-align: left;
        }
        .einstieg-hint strong { color: #991b1b; }
        .einstieg-cta {
            text-align: center;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_session_state() -> None:
    if "selected_broad_categories" not in st.session_state:
        st.session_state["selected_broad_categories"] = set()


def main() -> None:
    _ensure_session_state()
    render_toolbar("einstieg")
    _einstieg_css()

    st.markdown(
        '<div class="einstieg-hero">'
        '<p class="einstieg-eyebrow">Schritt 1 von 4</p>'
        '<p class="einstieg-title">Welche Musikrichtungen gefallen Dir?</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="einstieg-desc">'
        "Wähle eine oder mehrere grobe Stilrichtungen, die zu dir passen. "
        "Im nächsten Schritt siehst du dazu passende Genre-Schwerpunkte "
        "und typische Künstler - dort markierst du, welcher Sound "
        "wirklich deinem Geschmack entspricht."
        "</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="einstieg-hint">'
        "<strong>So startest du:</strong> Es reicht, wenn du alles ankreuzt, "
        "das grundsätzlich in Frage kommt. Feinjustierung und Künstler "
        "kommen gleich danach in Schritt 2."
        "</div>",
        unsafe_allow_html=True,
    )

    broad_categories, _ = load_broad_categories_res_10()

    if not broad_categories:
        st.warning(
            "Keine Stil-Kategorien in den Daten gefunden. Bitte zuerst "
            "`hatch run community-broad-categories` ausführen.",
        )
    else:
        selected: set[str] = set(
            st.session_state["selected_broad_categories"],
        )

        for cat in broad_categories:
            key = f"broad_cat_{cat}"
            checked = st.checkbox(
                cat,
                key=key,
                value=(cat in selected),
            )
            if checked:
                selected.add(cat)
            else:
                selected.discard(cat)

        st.session_state["selected_broad_categories"] = selected

        if selected:
            st.caption("Ausgewählt: " + ", ".join(sorted(selected)))

    st.markdown('<div class="einstieg-cta">', unsafe_allow_html=True)
    st.page_link(
        "pages/1_Community_Auswahl.py",
        label="Weiter zu Schritt 2",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
