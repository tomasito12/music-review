"""Tests for profile sign-in helpers and guest-flow session state."""

from __future__ import annotations

from typing import Any

import pytest
from pages.profil_auth_actions import (
    GUEST_FLOW_LOGIN,
    GUEST_FLOW_REGISTER,
    PROFIL_GUEST_FLOW_PENDING_KEY,
    PROFIL_GUEST_FLOW_RADIO_KEY,
    apply_pending_guest_flow_to_radio_state,
    run_sign_in,
)


def test_apply_pending_sets_radio_when_register() -> None:
    state: dict[str, Any] = {
        PROFIL_GUEST_FLOW_PENDING_KEY: GUEST_FLOW_REGISTER,
    }
    apply_pending_guest_flow_to_radio_state(state)
    assert PROFIL_GUEST_FLOW_PENDING_KEY not in state
    assert state[PROFIL_GUEST_FLOW_RADIO_KEY] == GUEST_FLOW_REGISTER


def test_apply_pending_ignores_unknown_value() -> None:
    state: dict[str, Any] = {PROFIL_GUEST_FLOW_PENDING_KEY: "not_a_flow"}
    apply_pending_guest_flow_to_radio_state(state)
    assert PROFIL_GUEST_FLOW_PENDING_KEY not in state
    assert PROFIL_GUEST_FLOW_RADIO_KEY not in state


def test_apply_pending_noop_when_missing() -> None:
    state: dict[str, Any] = {PROFIL_GUEST_FLOW_RADIO_KEY: GUEST_FLOW_LOGIN}
    apply_pending_guest_flow_to_radio_state(state)
    assert state[PROFIL_GUEST_FLOW_RADIO_KEY] == GUEST_FLOW_LOGIN


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
