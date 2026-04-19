"""Grobe Stilrichtungen auswählen (erster Schritt vor der feinen Musikauswahl)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    has_step1_state,
    load_broad_categories_res_10,
    render_toolbar,
    reset_step1_cascade,
)


def _einstieg_css() -> None:
    """Match Schritt-2-Seite: zentriert, rote Eyebrow."""
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
        .einstieg-column {
            max-width: 34rem;
            margin: 0 auto;
            text-align: center;
        }
        .einstieg-desc {
            margin: 0 0 0.85rem 0;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.58;
            text-align: center;
        }
        /* Streamlit markdown host: keep intro block centered */
        div[data-testid="stMarkdownContainer"]:has(.einstieg-column) {
            text-align: center !important;
        }
        .einstieg-cta {
            max-width: 34rem;
            margin: 1.5rem auto 1.5rem auto;
        }
        /* Schritt 1: Checkbox-Block schmaler und in der Mitte der Seite */
        section[data-testid="stMain"]:has(.einstieg-hero)
            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) {
            justify-content: center;
        }
        section[data-testid="stMain"]:has(.einstieg-hero)
            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"])
            [data-testid="element-container"] {
            display: flex;
            justify-content: center;
        }
        section[data-testid="stMain"]:has(.einstieg-hero)
            [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"])
            [data-testid="stCheckbox"] label {
            margin-left: auto;
            margin-right: auto;
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
        '<p class="einstieg-eyebrow">Schritt 1 von 3</p>'
        '<p class="einstieg-title">Welche Musikrichtungen gefallen Dir?</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="einstieg-column">'
        '<p class="einstieg-desc">'
        "Wähle eine oder mehrere grobe Stilrichtungen, die zu dir passen. "
        "Im nächsten Schritt siehst du dazu passende Genre-Schwerpunkte "
        "und typische Künstler - dort markierst du, welcher Sound "
        "wirklich deinem Geschmack entspricht."
        "</p>"
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

        # Symmetric layout; middle column wide enough for long category labels
        _pad_l, sp_mid, _pad_r = st.columns([1, 2, 1])
        with sp_mid:
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

    st.markdown('<div class="einstieg-cta">', unsafe_allow_html=True)
    if has_step1_state():
        st.button(
            "Auswahl zurücksetzen",
            type="secondary",
            width="stretch",
            key="einstieg_reset_cascade",
            on_click=reset_step1_cascade,
        )
    if st.button(
        "Weiter zu Schritt 2",
        type="primary",
        width="stretch",
        key="einstieg_next_step2",
    ):
        st.switch_page("pages/1_Community_Auswahl.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
