"""Tests for profile sign-in and registration helpers."""

from __future__ import annotations

import pytest
from pages.profil_auth_actions import run_register, run_sign_in


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
