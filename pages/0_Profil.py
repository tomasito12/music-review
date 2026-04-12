"""Profile page -- login, register, change password, or skip (German UI)."""

from __future__ import annotations

import streamlit as st
from pages.page_helpers import (
    build_session_profile_payload,
    clear_session_token_cookie,
    logout_active_profile,
    persist_active_profile_slug_cookie,
    reset_taste_preferences,
    session_taste_setup_complete,
)
from pages.profil_auth_actions import (
    GUEST_FLOW_LOGIN,
    GUEST_FLOW_OPTIONS,
    GUEST_FLOW_REGISTER,
    GUEST_FLOW_SKIP,
    PROFIL_GUEST_FLOW_RADIO_KEY,
    apply_pending_guest_flow_to_radio_state,
    run_sign_in,
)

from music_review.dashboard.user_db import (
    authenticate_user,
    change_password,
    create_user,
    get_connection,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    normalize_profile_slug,
    save_profile,
)

KEY_PROFILE_NAME = "profil_page_name_input"
KEY_PROFILE_SIGN_IN = "profil_page_sign_in"
KEY_PROFILE_SIGN_OUT = "profil_page_sign_out"
KEY_EXISTING_NAME = "profil_page_existing_name_input"
KEY_EXISTING_PASSWORD = "profil_page_existing_pw_input"
KEY_NEW_NAME = "profil_page_new_name_input"
KEY_NEW_PASSWORD = "profil_page_new_pw_input"
KEY_NEW_PASSWORD_CONFIRM = "profil_page_new_pw_confirm"
KEY_CHANGE_PW_OLD = "profil_page_change_pw_old"
KEY_CHANGE_PW_NEW = "profil_page_change_pw_new"
KEY_CHANGE_PW_CONFIRM = "profil_page_change_pw_confirm"

_MIN_PASSWORD_LENGTH = 4


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


def _create_new(name_raw: str, password: str, password_confirm: str) -> None:
    try:
        slug = normalize_profile_slug(name_raw)
    except ValueError as err:
        st.error(str(err))
        return
    if not password or len(password) < _MIN_PASSWORD_LENGTH:
        st.error(f"Passwort muss mindestens {_MIN_PASSWORD_LENGTH} Zeichen lang sein.")
        return
    if password != password_confirm:
        st.error("Passwörter stimmen nicht überein.")
        return
    conn = get_connection()
    if not create_user(conn, slug, password):
        st.error(
            "Ein Profil mit diesem Namen existiert bereits. "
            "Wenn es dein Profil ist, melde dich unter "
            "\u201eAnmelden\u201c mit demselben Namen an. "
            "Andernfalls wähle einen anderen Namen.",
        )
        return
    payload = build_session_profile_payload(profile_slug=slug)
    save_profile(None, slug, payload)  # type: ignore[arg-type]
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug
    persist_active_profile_slug_cookie(slug)
    apply_profile_to_session(st.session_state, payload)
    st.rerun()


def _render_change_password() -> None:
    """Expander to change the password of the logged-in user."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        return
    with st.expander("Passwort ändern"):
        old_pw = st.text_input(
            "Aktuelles Passwort",
            type="password",
            key=KEY_CHANGE_PW_OLD,
        )
        new_pw = st.text_input(
            "Neues Passwort",
            type="password",
            key=KEY_CHANGE_PW_NEW,
        )
        new_pw_confirm = st.text_input(
            "Neues Passwort bestätigen",
            type="password",
            key=KEY_CHANGE_PW_CONFIRM,
        )
        if st.button("Passwort ändern", key="profil_change_pw_btn"):
            if not old_pw:
                st.error("Bitte gib dein aktuelles Passwort ein.")
                return
            conn = get_connection()
            if not authenticate_user(conn, active, old_pw):
                st.error("Aktuelles Passwort ist falsch.")
                return
            if not new_pw or len(new_pw) < _MIN_PASSWORD_LENGTH:
                st.error(
                    f"Neues Passwort muss mindestens "
                    f"{_MIN_PASSWORD_LENGTH} Zeichen haben."
                )
                return
            if new_pw != new_pw_confirm:
                st.error("Neue Passwörter stimmen nicht überein.")
                return
            change_password(conn, active, new_pw)
            st.success("Passwort wurde geändert.")


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
            width="stretch",
        ):
            logout_active_profile()
            st.rerun()

    _render_change_password()


def _render_profile_choices() -> None:
    """Guest flow: login, register, or continue without a profile (radio)."""
    apply_pending_guest_flow_to_radio_state(st.session_state)
    flow_choice = st.radio(
        "Wie möchtest du fortfahren?",
        options=list(GUEST_FLOW_OPTIONS),
        horizontal=True,
        key=PROFIL_GUEST_FLOW_RADIO_KEY,
    )

    if flow_choice == GUEST_FLOW_LOGIN:
        st.markdown("> Gib deinen Profilnamen und dein Passwort ein.")
        st.caption(
            "Ohne Leerzeichen im Namen, bitte "
            "(Bindestrich oder Unterstrich sind erlaubt).",
        )
        existing_name = st.text_input(
            "Profilname",
            value="",
            placeholder="z. B. thomas",
            key=KEY_EXISTING_NAME,
        )
        existing_pw = st.text_input(
            "Passwort",
            type="password",
            key=KEY_EXISTING_PASSWORD,
        )
        if st.button("Anmelden", key=KEY_PROFILE_SIGN_IN):
            run_sign_in(existing_name, existing_pw)

    elif flow_choice == GUEST_FLOW_REGISTER:
        st.caption(
            "Ohne Leerzeichen im Namen, bitte "
            "(Bindestrich oder Unterstrich sind erlaubt).",
        )
        name_raw = st.text_input(
            "Profilname",
            value="",
            placeholder="z. B. thomas",
            key=KEY_NEW_NAME,
        )
        new_pw = st.text_input(
            "Passwort",
            type="password",
            key=KEY_NEW_PASSWORD,
        )
        new_pw_confirm = st.text_input(
            "Passwort bestätigen",
            type="password",
            key=KEY_NEW_PASSWORD_CONFIRM,
        )
        if st.button("Profil erstellen", key="profil_page_create"):
            _create_new(name_raw, new_pw, new_pw_confirm)

    elif flow_choice == GUEST_FLOW_SKIP:
        st.markdown(
            "Du kannst die App auch ohne Profil nutzen. "
            "Deine Auswahl geht dann verloren, sobald du den "
            "Browser-Tab schließt.",
        )
        if st.button(
            "Ohne Profil weiter",
            key="profil_page_skip",
            width="stretch",
        ):
            st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
            clear_session_token_cookie()
            st.session_state["flow_mode"] = None
            st.switch_page("pages/0b_Einstieg.py")


def main() -> None:
    if "flow_mode" not in st.session_state:
        st.session_state["flow_mode"] = None

    _profil_css()

    st.markdown(
        '<div class="profil-hero">'
        '<p class="profil-title">Profil</p>'
        '<p class="profil-subtitle">'
        "Melde dich an oder erstelle ein neues Profil"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="profil-body">'
        "<p>"
        "Dein Musikgeschmack wird unter deinem Profilnamen gespeichert "
        "und mit einem Passwort geschützt. Beim nächsten Besuch kannst du "
        "direkt weitermachen."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="profil-benefit">'
        "<strong>Warum ein Profil?</strong> "
        "Dein Musikgeschmack (Stil-Schwerpunkte, Genre-Filter, "
        "Gewichtungen) wird gespeichert. Beim nächsten Besuch kannst du "
        "direkt nach neuer Musik stöbern, ohne die Auswahl erneut "
        "von vorn zu durchlaufen."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Filter und Stile zurücksetzen"):
        st.markdown(
            "Leert Stil- und Filtereinstellungen in dieser Sitzung. "
            "Dein gespeichertes Profil bleibt unverändert, bis du "
            "in der Seitenleiste **Speichern** wählst."
        )
        confirm = st.checkbox(
            "Ja, Filter und Stile zurücksetzen.",
            key="profil_reset_confirm",
        )
        if st.button(
            "Filter und Stile zurücksetzen",
            disabled=not confirm,
            key="profil_reset_run",
        ):
            reset_taste_preferences()
            st.switch_page("pages/0b_Einstieg.py")

    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if active:
        _render_active_profile()
    else:
        _render_profile_choices()

    st.markdown('<div class="profil-cta">', unsafe_allow_html=True)
    if st.button("Weiter", type="primary", width="stretch", key="profil_page_weiter"):
        if session_taste_setup_complete():
            st.switch_page("pages/2_Entdecken.py")
        else:
            st.switch_page("pages/0b_Einstieg.py")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
