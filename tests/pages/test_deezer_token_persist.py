"""Tests for the Deezer token persistence helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pages import deezer_token_persist as dtp

from music_review.dashboard.deezer_oauth_token_json import deezer_token_to_json_str
from music_review.dashboard.user_db import (
    create_user,
    get_connection,
    load_deezer_oauth_token_json,
    save_deezer_oauth_token,
)
from music_review.integrations.deezer_client import DeezerToken


@pytest.fixture()
def db_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Patch ``get_connection`` so the token persist module hits an isolated DB."""
    db_path = tmp_path / "users.db"
    conn = get_connection(db_path)
    monkeypatch.setattr(dtp, "get_connection", lambda: get_connection(db_path))
    return conn


def _session_state_with_user(slug: str | None) -> dict[str, object]:
    state: dict[str, object] = {}
    if slug is not None:
        state["active_profile_slug"] = slug
    return state


def _patch_session(monkeypatch: pytest.MonkeyPatch, state: dict[str, object]) -> None:
    monkeypatch.setattr("pages.deezer_token_persist.st.session_state", state)
    monkeypatch.setattr(
        "pages.deezer_token_persist.st.query_params",
        {},
    )


def _make_token() -> DeezerToken:
    return DeezerToken(
        access_token="acc-1",
        expires_in=0,
        obtained_at=datetime(2030, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


def test_read_token_from_session_returns_none_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _session_state_with_user(None)
    _patch_session(monkeypatch, state)
    assert dtp.read_deezer_token_from_session() is None


def test_read_token_from_session_parses_dict_with_iso_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _session_state_with_user("alice")
    state[dtp.DEEZER_TOKEN_SESSION_KEY] = {
        "access_token": "tok",
        "expires_in": 0,
        "obtained_at": "2030-01-01T00:00:00Z",
    }
    _patch_session(monkeypatch, state)
    token = dtp.read_deezer_token_from_session()
    assert token is not None
    assert token.access_token == "tok"
    assert token.obtained_at.year == 2030


def test_read_token_from_session_returns_none_for_invalid_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _session_state_with_user("alice")
    state[dtp.DEEZER_TOKEN_SESSION_KEY] = {"only": "junk"}
    _patch_session(monkeypatch, state)
    assert dtp.read_deezer_token_from_session() is None


def test_persist_token_writes_to_session_only_when_no_active_user(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    state = _session_state_with_user(None)
    _patch_session(monkeypatch, state)
    dtp.persist_deezer_token(_make_token())
    assert dtp.DEEZER_TOKEN_SESSION_KEY in state


def test_persist_token_writes_to_db_when_active_user(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    create_user(db_factory, "alice", "pw")
    state = _session_state_with_user("alice")
    _patch_session(monkeypatch, state)
    dtp.persist_deezer_token(_make_token())
    blob = load_deezer_oauth_token_json(db_factory, "alice")
    assert blob is not None
    assert "acc-1" in blob


def test_hydrate_returns_false_when_no_active_user(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    state = _session_state_with_user(None)
    _patch_session(monkeypatch, state)
    assert dtp.hydrate_deezer_token_from_db_for_active_user() is False


def test_hydrate_returns_false_when_session_already_has_token(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    state = _session_state_with_user("alice")
    state[dtp.DEEZER_TOKEN_SESSION_KEY] = {
        "access_token": "session-tok",
        "expires_in": 0,
        "obtained_at": "2030-01-01T00:00:00Z",
    }
    _patch_session(monkeypatch, state)
    assert dtp.hydrate_deezer_token_from_db_for_active_user() is False


def test_hydrate_loads_token_from_db_into_session(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    create_user(db_factory, "alice", "pw")
    save_deezer_oauth_token(
        db_factory, "alice", deezer_token_to_json_str(_make_token())
    )
    state = _session_state_with_user("alice")
    _patch_session(monkeypatch, state)
    assert dtp.hydrate_deezer_token_from_db_for_active_user() is True
    assert state[dtp.DEEZER_TOKEN_SESSION_KEY]["access_token"] == "acc-1"


def test_hydrate_skips_when_oauth_callback_query_params_present(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    create_user(db_factory, "alice", "pw")
    save_deezer_oauth_token(
        db_factory, "alice", deezer_token_to_json_str(_make_token())
    )
    state = _session_state_with_user("alice")
    monkeypatch.setattr("pages.deezer_token_persist.st.session_state", state)
    monkeypatch.setattr(
        "pages.deezer_token_persist.st.query_params",
        {"code": "abc", "state": "xyz"},
    )
    assert dtp.hydrate_deezer_token_from_db_for_active_user() is False
    assert dtp.DEEZER_TOKEN_SESSION_KEY not in state


def test_clear_persisted_token_removes_from_session_and_db(
    monkeypatch: pytest.MonkeyPatch,
    db_factory,
) -> None:
    create_user(db_factory, "alice", "pw")
    save_deezer_oauth_token(
        db_factory, "alice", deezer_token_to_json_str(_make_token())
    )
    state = _session_state_with_user("alice")
    state[dtp.DEEZER_TOKEN_SESSION_KEY] = {
        "access_token": "tok",
        "expires_in": 0,
        "obtained_at": "2030-01-01T00:00:00Z",
    }
    _patch_session(monkeypatch, state)
    dtp.clear_persisted_deezer_token_for_active_user()
    assert dtp.DEEZER_TOKEN_SESSION_KEY not in state
    assert load_deezer_oauth_token_json(db_factory, "alice") is None
