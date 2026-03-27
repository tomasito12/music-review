"""Grobkategorie-Auswahl als erster Schritt der Community-Selektion."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import load_broad_categories_res_10, render_toolbar


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
            text-align: center;
        }
        .einstieg-desc {
            max-width: 38rem;
            margin: 0 auto 1.3rem auto;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.55;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_session_state() -> None:
    if "selected_broad_categories" not in st.session_state:
        st.session_state["selected_broad_categories"] = set()


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar -- Einstieg",
        page_icon=None,
        layout="centered",
    )

    _ensure_session_state()
    render_toolbar("einstieg")
    _einstieg_css()

    st.markdown(
        '<p class="einstieg-title">Welche Musikrichtungen interessieren dich?</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="einstieg-desc">'
        "Wähle eine oder mehrere Grobkategorien aus. "
        "Im nächsten Schritt siehst du die darin enthaltenen "
        "Communities und kannst gezielt auswählen."
        "</p>",
        unsafe_allow_html=True,
    )

    broad_categories, category_mappings = load_broad_categories_res_10()

    if not broad_categories:
        st.warning(
            "Keine Grobkategorien gefunden. Bitte zuerst "
            "`hatch run community-broad-categories` ausführen.",
        )
    else:
        selected: set[str] = set(
            st.session_state["selected_broad_categories"],
        )

        for cat in broad_categories:
            n_communities = sum(
                1 for bc_list in category_mappings.values() if cat in bc_list
            )
            label = f"{cat}  ({n_communities} Communities)"
            key = f"broad_cat_{cat}"
            checked = st.checkbox(
                label,
                key=key,
                value=(cat in selected),
            )
            if checked:
                selected.add(cat)
            else:
                selected.discard(cat)

        st.session_state["selected_broad_categories"] = selected

        if selected:
            st.caption(
                f"**{len(selected)}** Kategorien ausgewählt: "
                + ", ".join(sorted(selected)),
            )

    if st.button("Weiter", type="primary", use_container_width=True):
        st.switch_page("pages/1_Community_Auswahl.py")


if __name__ == "__main__":
    main()
