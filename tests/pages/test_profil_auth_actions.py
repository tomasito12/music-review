"""Tests for profile sign-in and registration helpers."""

from __future__ import annotations

import pytest
from pages.page_helpers import WIZARD_ACCOUNT_SAVE_INTENT_KEY
from pages.profil_auth_actions import run_register, run_sign_in

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    LOGIN_PROFILE_MERGE_PENDING_KEY,
    build_profile_payload,
)


def test_run_sign_in_empty_name_shows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []

    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda msg: errors.append(str(msg)),
    )
    monkeypatch.setattr("pages.profil_auth_actions.st.rerun", lambda: None)

    run_sign_in("   ", "secret")
    assert errors == ["Bitte gib einen Profilnamen ein."]


def test_run_sign_in_empty_password_error(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []

    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda msg: errors.append(str(msg)),
    )
    monkeypatch.setattr("pages.profil_auth_actions.st.rerun", lambda: None)

    run_sign_in("valid-name", "")
    assert errors == ["Bitte gib dein Passwort ein."]


def test_run_register_empty_name_error(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []

    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda msg: errors.append(str(msg)),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.switch_page",
        lambda _path: None,
    )

    run_register("  ", "abcd", "abcd")
    assert errors == ["Bitte gib einen Benutzernamen ein."]


def test_run_register_short_password_error(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []
    switches: list[str] = []

    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda msg: errors.append(str(msg)),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.switch_page",
        lambda path: switches.append(path),
    )

    run_register("valid-name", "12", "12")
    assert errors
    assert not switches


def _session_state_with_complete_taste() -> dict[str, object]:
    return {
        "selected_communities": {"1"},
        "artist_flow_selected_communities": {"1"},
        "genre_flow_selected_communities": set(),
        "filter_settings": {
            "year_min": 1990,
            "year_max": 2020,
            "rating_min": 0,
            "rating_max": 10,
        },
        "community_weights_raw": {"1": 1.0},
    }


def _server_profile_complete(*, slug: str = "alice") -> dict[str, object]:
    return build_profile_payload(
        profile_slug=slug,
        flow_mode="combined",
        selected_communities={"99"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"99": 1.0},
    )


def test_run_sign_in_sets_merge_pending_when_guest_session_has_prefs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _server_profile_complete()
    state = _session_state_with_complete_taste()
    monkeypatch.setattr("pages.profil_auth_actions.st.session_state", state)
    monkeypatch.setattr("pages.profil_auth_actions.st.rerun", lambda: None)
    monkeypatch.setattr(
        "pages.profil_auth_actions.load_profile",
        lambda *_a, **_k: server,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.user_exists",
        lambda _c, _s: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.authenticate_user",
        lambda _c, _s, _p: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.get_connection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.persist_active_profile_slug_cookie",
        lambda _s: None,
    )

    run_sign_in("alice", "secret")

    pending = state.get(LOGIN_PROFILE_MERGE_PENDING_KEY)
    assert isinstance(pending, dict)
    assert pending.get("server_profile") == server
    assert state[ACTIVE_PROFILE_SESSION_KEY] == "alice"
    assert state["selected_communities"] == {"1"}


def test_run_sign_in_applies_server_when_no_guest_prefs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _server_profile_complete()
    state: dict[str, object] = {}
    monkeypatch.setattr("pages.profil_auth_actions.st.session_state", state)
    monkeypatch.setattr("pages.profil_auth_actions.st.rerun", lambda: None)
    monkeypatch.setattr(
        "pages.profil_auth_actions.load_profile",
        lambda *_a, **_k: server,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.user_exists",
        lambda _c, _s: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.authenticate_user",
        lambda _c, _s, _p: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.get_connection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.persist_active_profile_slug_cookie",
        lambda _s: None,
    )

    run_sign_in("alice", "secret")

    assert LOGIN_PROFILE_MERGE_PENDING_KEY not in state
    assert state["selected_communities"] == {"99"}


def test_run_register_routes_to_entdecken_when_taste_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _session_state_with_complete_taste()
    monkeypatch.setattr("pages.profil_auth_actions.st.session_state", state)
    switches: list[str] = []
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.switch_page",
        lambda path: switches.append(path),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.get_connection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.create_user",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.save_profile",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.persist_active_profile_slug_cookie",
        lambda _s: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.session_taste_setup_complete",
        lambda: True,
    )

    run_register("newslug", "abcd", "abcd")

    assert switches == ["pages/2_Entdecken.py"]
    assert WIZARD_ACCOUNT_SAVE_INTENT_KEY not in state


def test_run_register_routes_to_einstieg_when_taste_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _session_state_with_complete_taste()
    monkeypatch.setattr("pages.profil_auth_actions.st.session_state", state)
    switches: list[str] = []
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.error",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.st.switch_page",
        lambda path: switches.append(path),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.get_connection",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.create_user",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.save_profile",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.persist_active_profile_slug_cookie",
        lambda _s: None,
    )
    monkeypatch.setattr(
        "pages.profil_auth_actions.session_taste_setup_complete",
        lambda: False,
    )

    run_register("otherslug", "abcd", "abcd")

    assert switches == ["pages/0b_Einstieg.py"]
