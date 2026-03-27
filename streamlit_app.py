#!/usr/bin/env python3
"""Start page for the multi-step music recommendation flow."""

from __future__ import annotations

import streamlit as st

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    build_profile_payload,
    default_profiles_dir,
    load_profile,
    normalize_profile_slug,
    save_profile,
)

KEY_PROFILE_NAME = "streamlit_profile_name_input"
KEY_PROFILE_SIGN_IN = "streamlit_profile_sign_in"
KEY_PROFILE_SAVE = "streamlit_profile_save"
KEY_PROFILE_SIGN_OUT = "streamlit_profile_sign_out"


def _render_profile_panel() -> None:
    """Passwordless profile: load/save JSON under data/user_profiles/."""
    profiles_dir = default_profiles_dir()
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)

    with st.expander(
        "Profil (ohne Passwort): laden und speichern",
        expanded=False,
    ):
        st.caption(
            "Gewaehlte Communities, Filter und Gewichte werden lokal in "
            "`data/user_profiles/` abgelegt. Ohne Passwortschutz: wer den Namen "
            "kennt, kann dasselbe Profil laden. Nur fuer vertrauenswuerdige "
            "Umgebungen geeignet.",
        )
        if active:
            st.success(f"Angemeldet als **{active}**")

        name_raw = st.text_input(
            "Profilname",
            value="",
            placeholder="z. B. anna oder mein-setup",
            key=KEY_PROFILE_NAME,
        )

        col_si, col_sv, col_so = st.columns(3)
        with col_si:
            if st.button("Anmelden", key=KEY_PROFILE_SIGN_IN):
                try:
                    slug_try = normalize_profile_slug(name_raw)
                except ValueError as err:
                    st.error(str(err))
                else:
                    data = load_profile(profiles_dir, slug_try)
                    if data is None:
                        st.error("Kein gespeichertes Profil unter diesem Namen.")
                    else:
                        apply_profile_to_session(st.session_state, data)
                        st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug_try
                        st.success(f"Profil '{slug_try}' geladen.")
                        st.rerun()
        with col_sv:
            if st.button("Speichern", key=KEY_PROFILE_SAVE):
                target = (active or name_raw).strip()
                try:
                    slug_save = normalize_profile_slug(target)
                except ValueError as err:
                    st.error(str(err))
                else:
                    artist = st.session_state.get("artist_flow_selected_communities")
                    if not isinstance(artist, set):
                        artist = set()
                    genre = st.session_state.get("genre_flow_selected_communities")
                    if not isinstance(genre, set):
                        genre = set()
                    fs = st.session_state.get("filter_settings")
                    if not isinstance(fs, dict):
                        fs = {}
                    weights = st.session_state.get("community_weights_raw")
                    if not isinstance(weights, dict):
                        weights = {}
                    payload = build_profile_payload(
                        profile_slug=slug_save,
                        flow_mode=st.session_state.get("flow_mode"),
                        artist_communities=artist,
                        genre_communities=genre,
                        filter_settings=fs,
                        community_weights_raw=weights,
                    )
                    save_profile(profiles_dir, slug_save, payload)
                    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug_save
                    st.success(f"Profil '{slug_save}' gespeichert.")
                    st.rerun()
        with col_so:
            if st.button("Abmelden", key=KEY_PROFILE_SIGN_OUT):
                st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
                st.info(
                    "Abgemeldet. Die aktuellen Einstellungen im Tab bleiben, bis "
                    "du sie aenderst oder ein Profil laedst.",
                )


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Start",
        page_icon="🎵",
        layout="wide",
    )

    # Flow-Modus Standard, wenn noch nicht gesetzt
    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    _render_profile_panel()

    st.title("🎵 Music Review Recommender")
    st.markdown(
        "**Wie möchtest du zu deinen Empfehlungen kommen?** "
        "Wähle einen Einstieg - du kannst später jederzeit zurück zur "
        "Startseite wechseln.",
    )

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Musik-Stile / Genres / Moods")
        st.caption(
            "Starte mit Communities, Genres und Moods. "
            "Ideal, wenn du eher eine Stimmung als konkrete Künstler im Kopf hast.",
        )
        if st.button("Diesen Weg wählen", key="start_genre_flow"):
            st.session_state["flow_mode"] = "genres"
            st.switch_page("pages/2_Genre_Flow.py")

    with col2:
        st.subheader("Artists")
        st.caption(
            "Starte mit Künstlern, die du magst, und entdecke ähnliche Alben "
            "über das Community- und RAG-System.",
        )
        if st.button("Diesen Weg wählen", key="start_artist_flow"):
            st.session_state["flow_mode"] = "artists"
            st.switch_page("pages/1_Artist_Flow.py")

    with col3:
        st.subheader("Beides kombinieren")
        st.caption(
            "Kombiniere Artist- und Genre/Mood-Signale zu einem mehrstufigen "
            "Recommender-Prozess.",
        )
        if st.button("Diesen Weg wählen", key="start_combined_flow"):
            st.session_state["flow_mode"] = "combined"
            st.switch_page("pages/1_Artist_Flow.py")

    st.markdown("---")
    st.caption(
        "Hinweis: Die bisherige Dashboard-Ansicht ist unter "
        "`archive/streamlit_app_legacy.py` weiterhin verfügbar. "
        "RAG-/Freitext-Diagnose: Sidebar-Seite **Freitext-Qualitaet**.",
    )


if __name__ == "__main__":
    main()
