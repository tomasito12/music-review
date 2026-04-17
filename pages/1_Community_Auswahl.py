"""Feine Stil- und Künstlerauswahl nach Grobkategorien (ohne Suche)."""

from __future__ import annotations

from typing import Any

import streamlit as st
from pages.page_helpers import (
    build_community_broad_category_index,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
    render_toolbar,
)


def _feinwahl_css() -> None:
    """Visual alignment with Einstieg/Profil: centered, compact."""
    st.markdown(
        """
        <style>
        /* One centered column for eyebrow, title, and intro (matches visual width). */
        .feinwahl-intro {
            max-width: 34rem;
            margin: 0 auto 0.85rem auto;
            text-align: center;
        }
        .feinwahl-hero {
            text-align: center;
            padding: 1.1rem 0.75rem 0.35rem 0.75rem;
        }
        .feinwahl-eyebrow {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.4rem;
        }
        .feinwahl-title {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
            color: #111827;
        }
        .feinwahl-desc {
            margin: 0;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.58;
            text-align: center;
        }
        div[data-testid="stMarkdownContainer"]:has(.feinwahl-intro) {
            text-align: center !important;
        }
        .feinwahl-cta {
            text-align: center;
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_session_state() -> None:
    if "selected_communities" not in st.session_state:
        st.session_state["selected_communities"] = set()
    if "selected_broad_categories" not in st.session_state:
        st.session_state["selected_broad_categories"] = set()


def _render_community_list(
    category: str,
    items: list[dict[str, Any]],
    selected: set[str],
    rendered_ids: set[str],
) -> set[str]:
    """Render checkboxes inside one category expander. Returns updated selection.

    Rows already in *rendered_ids* are skipped (overlap across categories).
    """
    visible = [item for item in items if item["id"] not in rendered_ids]
    if not visible:
        return selected

    with st.expander(category, expanded=False):
        for item in visible:
            cid = item["id"]
            rendered_ids.add(cid)
            artists_str = ", ".join(item["top_artists"])
            label = f"**{item['genre_label']}** - {artists_str}"
            key = f"comm_sel_{cid}"
            checked = st.checkbox(
                label,
                key=key,
                value=(cid in selected),
            )
            if checked:
                selected.add(cid)
            else:
                selected.discard(cid)
    return selected


def main() -> None:
    _ensure_session_state()
    render_toolbar("community_auswahl")
    _feinwahl_css()

    st.markdown(
        '<div class="feinwahl-intro">'
        '<div class="feinwahl-hero">'
        '<p class="feinwahl-eyebrow">Schritt 2 von 3</p>'
        '<p class="feinwahl-title">Dein Sound im Detail</p>'
        "</div>"
        '<p class="feinwahl-desc">'
        "Hier geht es um die Feinjustierung: Zu jeder groben Richtung von eben "
        "gibt es konkrete Genre-Bezeichnungen und typische Künstlerinnen "
        "und Künstler. "
        "<strong>Mehrfachauswahl ist erwünscht</strong>: je mehr Treffer, "
        "desto klarer wird dein Profil."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()
    _broad_cats, category_mappings = load_broad_categories_res_10()

    if not communities:
        st.warning(
            "Keine Stilgruppen in den Daten gefunden. Bitte zuerst "
            "`hatch run graph-build -- --export-communities 10` ausführen.",
        )
    else:
        selected_broad = st.session_state.get(
            "selected_broad_categories",
            set(),
        )
        community_index = build_community_broad_category_index(
            communities,
            genre_labels,
            category_mappings,
        )

        selected: set[str] = set(
            st.session_state["selected_communities"],
        )

        if selected_broad:
            active_cats = sorted(
                cat for cat in community_index if cat in selected_broad
            )
        else:
            active_cats = sorted(community_index.keys())

        rendered_ids: set[str] = set()
        for cat in active_cats:
            items = community_index.get(cat, [])
            selected = _render_community_list(
                cat,
                items,
                selected,
                rendered_ids,
            )

        st.session_state["selected_communities"] = selected

    st.markdown('<div class="feinwahl-cta">', unsafe_allow_html=True)
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button(
            "Zurück zu Schritt 1",
            type="secondary",
            width="stretch",
            key="feinwahl_back_step1",
        ):
            st.switch_page("pages/0b_Einstieg.py")
    with col_next:
        if st.button(
            "Weiter zu Schritt 3",
            type="primary",
            width="stretch",
            key="feinwahl_next_step3",
        ):
            st.switch_page("pages/5_Filter_Flow.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
