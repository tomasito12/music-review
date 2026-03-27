"""Eigenständige Profilseite -- Profil laden, anlegen oder überspringen."""

from __future__ import annotations

from typing import Any

import streamlit as st

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    build_profile_payload,
    default_profiles_dir,
    list_profile_slugs,
    load_profile,
    normalize_profile_slug,
    save_profile,
)

KEY_PROFILE_NAME = "profil_page_name_input"
KEY_PROFILE_SIGN_IN = "profil_page_sign_in"
KEY_PROFILE_SIGN_OUT = "profil_page_sign_out"
KEY_EXISTING_SELECT = "profil_page_existing_select"

_NO_SELECTION = "(kein Profil ausgewählt)"


def _profil_css() -> None:
    st.markdown(
        """
        <style>
        .profil-hero {
            text-align: center;
            padding: 2.5rem 1rem 1rem 1rem;
        }
        .profil-title {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.3rem;
            color: #111827;
        }
        .profil-subtitle {
            font-size: 1.05rem;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }
        .profil-body {
            max-width: 38rem;
            margin: 0 auto;
            font-size: 1rem;
            line-height: 1.7;
            color: #374151;
            text-align: left;
        }
        .profil-body p {
            margin-bottom: 1rem;
        }
        .profil-benefit {
            max-width: 38rem;
            margin: 0 auto 1.5rem auto;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            font-size: 0.88rem;
            color: #1e3a5f;
            line-height: 1.55;
        }
        .profil-cta {
            text-align: center;
            margin-top: 2rem;
            margin-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sign_in(profiles_dir: Any, slug: str) -> None:
    try:
        safe = normalize_profile_slug(slug)
    except ValueError as err:
        st.error(str(err))
        return
    data = load_profile(profiles_dir, safe)
    if data is None:
        st.error("Profil konnte nicht geladen werden.")
        return
    apply_profile_to_session(st.session_state, data)
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = safe
    st.rerun()


def _create_new(profiles_dir: Any, name_raw: str) -> None:
    try:
        slug = normalize_profile_slug(name_raw)
    except ValueError as err:
        st.error(str(err))
        return
    existing_data = load_profile(profiles_dir, slug)
    if existing_data is not None:
        st.error(
            f"Ein Profil mit dem Namen '{slug}' existiert bereits. "
            "Bitte wähle es unter 'Bestehendes Profil' oder verwende "
            "einen anderen Namen.",
        )
        return
    payload = build_profile_payload(
        profile_slug=slug,
        flow_mode=None,
        artist_communities=set(),
        genre_communities=set(),
        filter_settings={},
        community_weights_raw={},
    )
    save_profile(profiles_dir, slug, payload)
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug
    st.rerun()


def _render_active_profile() -> None:
    """Show status and actions when a profile is already loaded."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        return

    with st.container(border=True):
        st.success(f"Angemeldet als **{active}**")
        if st.button(
            "Abmelden",
            key=KEY_PROFILE_SIGN_OUT,
            use_container_width=True,
        ):
            st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
            st.rerun()


def _render_profile_choices() -> None:
    """Three-tab profile selection: existing / new / skip."""
    profiles_dir = default_profiles_dir()
    existing = list_profile_slugs(profiles_dir)

    tab_existing, tab_new, tab_skip = st.tabs(
        [
            "Bestehendes Profil laden",
            "Neues Profil anlegen",
            "Ohne Profil weiter",
        ]
    )

    with tab_existing:
        if existing:
            options: list[str] = [_NO_SELECTION, *existing]
            choice = st.selectbox(
                "Profil auswählen",
                options=options,
                index=0,
                key=KEY_EXISTING_SELECT,
            )
            if st.button("Anmelden", key=KEY_PROFILE_SIGN_IN):
                if choice == _NO_SELECTION:
                    st.error("Bitte wähle ein Profil aus der Liste.")
                else:
                    _sign_in(profiles_dir, str(choice))
        else:
            st.info(
                "Noch keine gespeicherten Profile vorhanden. "
                "Lege ein neues Profil an oder starte ohne Profil.",
            )

    with tab_new:
        name_raw = st.text_input(
            "Profilname",
            value="",
            placeholder="z. B. anna oder mein-setup",
            key=KEY_PROFILE_NAME,
        )
        if st.button("Profil erstellen", key="profil_page_create"):
            _create_new(profiles_dir, name_raw)

    with tab_skip:
        st.markdown(
            "Du kannst die App auch ohne Profil nutzen. "
            "Deine Auswahl geht dann verloren, sobald du den "
            "Browser-Tab schließt.",
        )
        if st.button(
            "Ohne Profil weiter",
            key="profil_page_skip",
            use_container_width=True,
        ):
            st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
            st.session_state["flow_mode"] = None
            st.switch_page("pages/0b_Einstieg.py")


def main() -> None:
    st.set_page_config(
        page_title="Plattenradar -- Profil",
        page_icon=None,
        layout="centered",
    )

    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    _profil_css()

    st.markdown(
        '<div class="profil-hero">'
        '<p class="profil-title">Profil</p>'
        '<p class="profil-subtitle">'
        "Melde dich an, um deinen Musikgeschmack zu speichern"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="profil-body">'
        "<p>"
        "Die App ist zunächst für den Freundeskreis gedacht. "
        "Dein Profilname genügt &mdash; bewusst ohne Passwort, "
        "weil wir uns vertrauen."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="profil-benefit">'
        "<strong>Warum ein Profil?</strong> "
        "Dein Musikgeschmack (gewählte Communities, Genre-Filter, "
        "Gewichtungen) wird gespeichert. Beim nächsten Besuch kannst du "
        "direkt nach neuer Musik stöbern, ohne den Genre- und "
        "Artist-Filter erneut durchzugehen."
        "</div>",
        unsafe_allow_html=True,
    )

    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if active:
        _render_active_profile()
    else:
        _render_profile_choices()

    st.markdown('<div class="profil-cta">', unsafe_allow_html=True)
    if st.button("Weiter", type="primary", use_container_width=True):
        st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
