"""Step 4 of 4: destination hub after filter and style setup (Streamlit page)."""

from __future__ import annotations

import streamlit as st
from pages.hub_destinations import hub_destinations
from pages.page_helpers import (
    ACTIVE_PROFILE_SESSION_KEY,
    render_toolbar,
    reset_taste_preferences,
    session_taste_setup_complete,
)


def _hub_css() -> None:
    st.markdown(
        """
        <style>
        .hub-hero {
            text-align: center;
            padding: 1.1rem 0.75rem 0.35rem 0.75rem;
        }
        .hub-eyebrow {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.4rem;
        }
        .hub-title {
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 0.2rem;
            color: #111827;
        }
        .hub-desc {
            max-width: 34rem;
            margin: 0 auto 1rem auto;
            color: #6b7280;
            font-size: 0.92rem;
            line-height: 1.58;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    render_toolbar("hub")
    _hub_css()

    st.markdown(
        '<div class="hub-hero">'
        '<p class="hub-eyebrow">Schritt 4 von 4</p>'
        '<p class="hub-title">Was möchtest du entdecken?</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hub-desc">'
        "Hier wählst du, womit du starten möchtest. Du kannst später "
        "jederzeit über die Seitenleiste zu den anderen Bereichen wechseln."
        "</p>",
        unsafe_allow_html=True,
    )

    if not session_taste_setup_complete():
        st.warning(
            "Bitte richte zuerst Filter und Stile ein "
            "(Stilrichtungen, Genre und Filter).",
        )
        if st.button(
            "Zur Einrichtung",
            type="primary",
            width="stretch",
            key="hub_incomplete_to_einstieg",
        ):
            st.switch_page("pages/0b_Einstieg.py")
        return

    destinations = hub_destinations()
    cols_per_row = 2
    for row_start in range(0, len(destinations), cols_per_row):
        row = destinations[row_start : row_start + cols_per_row]
        columns = st.columns(len(row), gap="medium")
        for col, dest in zip(columns, row, strict=True):
            with col, st.container(border=True):
                st.markdown(f"**{dest.title}**")
                st.caption(dest.description)
                key = f"hub_nav_{dest.page_path}_{row_start}"
                if st.button("Öffnen", key=key, width="stretch"):
                    st.switch_page(dest.page_path)

    st.markdown("---")
    st.caption("Feintuning")
    ft1, ft2 = st.columns(2)
    with ft1:
        st.page_link(
            "pages/5_Filter_Flow.py",
            label="Gewichte und Filter",
            use_container_width=True,
        )
    with ft2:
        st.page_link(
            "pages/1_Community_Auswahl.py",
            label="Stil-Schwerpunkte",
            use_container_width=True,
        )

    with st.expander("Filter und Stile zurücksetzen"):
        st.markdown(
            "Alle Stil- und Filtereinstellungen in dieser Sitzung werden "
            "gelöscht. Wenn du angemeldet bist, bleibt die gespeicherte "
            "Profil-Datei unverändert, bis du in der Seitenleiste auf "
            "**Speichern** klickst."
        )
        confirm = st.checkbox(
            "Ja, Filter und Stile zurücksetzen.",
            key="hub_reset_confirm",
        )
        if st.button(
            "Filter und Stile zurücksetzen",
            disabled=not confirm,
            key="hub_reset_run",
        ):
            reset_taste_preferences()
            st.switch_page("pages/0b_Einstieg.py")

    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if active:
        st.caption(
            f"Angemeldet als **{active}** -- nach einem Reset ggf. "
            "**Speichern**, damit das Profil auf der Platte mitzieht."
        )


if __name__ == "__main__":
    main()
