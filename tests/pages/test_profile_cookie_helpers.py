"""Tests for profile cookie helpers (session-token-based login)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pages import profile_session

from music_review.dashboard.user_db import (
    create_user,
    get_connection,
    save_user_profile,
    validate_session_token,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    build_profile_payload,
)


@pytest.fixture()
def test_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide a per-test DB and wire it into profile_session + profile store."""
    db_path = tmp_path / "cookie_test.db"
    conn = get_connection(db_path)
    monkeypatch.setattr(
        profile_session,
        "get_db_connection",
        lambda: conn,
    )
    monkeypatch.setattr(
        "music_review.dashboard.user_profile_store.get_connection",
        lambda: conn,
    )
    monkeypatch.setattr(
        "music_review.dashboard.user_profile_store._db_conn",
        lambda: conn,
    )
    return conn


def test_persist_active_profile_slug_cookie_skips_invalid_slug(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    mock_cm = MagicMock()
    monkeypatch.setattr(
        profile_session,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    profile_session.persist_active_profile_slug_cookie("!!!")
    mock_cm.set.assert_not_called()


def test_persist_active_profile_slug_cookie_creates_session_token(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    create_user(test_db, "ada", "pw")
    mock_cm = MagicMock()
    monkeypatch.setattr(
        profile_session,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    profile_session.persist_active_profile_slug_cookie("Ada")
    mock_cm.set.assert_called_once()
    args, kwargs = mock_cm.set.call_args
    assert args[0] == profile_session.SESSION_TOKEN_COOKIE_NAME
    assert kwargs.get("same_site") == "lax"
    token = args[1]
    slug = validate_session_token(test_db, token)
    assert slug == "ada"


def test_clear_active_profile_slug_cookie_deletes_both_cookies(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    mock_cm = MagicMock()
    monkeypatch.setattr(
        profile_session,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    monkeypatch.setattr(
        profile_session,
        "_read_session_token_from_cookies",
        lambda: None,
    )
    profile_session.clear_active_profile_slug_cookie()
    delete_calls = mock_cm.delete.call_args_list
    deleted_names = {c.args[0] for c in delete_calls}
    assert profile_session.SESSION_TOKEN_COOKIE_NAME in deleted_names


def test_restore_from_cookie_skips_when_session_has_slug(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    sess = {ACTIVE_PROFILE_SESSION_KEY: "ada"}
    monkeypatch.setattr(profile_session.st, "session_state", sess)
    profile_session.restore_active_profile_from_cookie_if_needed()


def test_restore_from_cookie_validates_token_and_hydrates(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    create_user(test_db, "bob", "pw")
    payload = build_profile_payload(
        profile_slug="bob",
        flow_mode=None,
        selected_communities={"C01"},
        filter_settings={"x": 1},
        community_weights_raw={"C01": 0.5},
    )
    save_user_profile(test_db, "bob", payload)
    from music_review.dashboard.user_db import create_session_token

    token = create_session_token(test_db, "bob")
    sess: dict[str, object] = {}
    monkeypatch.setattr(profile_session.st, "session_state", sess)
    monkeypatch.setattr(
        profile_session,
        "_read_session_token_from_cookies",
        lambda: token,
    )
    profile_session.restore_active_profile_from_cookie_if_needed()
    assert sess[ACTIVE_PROFILE_SESSION_KEY] == "bob"
    assert sess["selected_communities"] == {"C01"}
    assert sess["filter_settings"] == {"x": 1}


def test_restore_from_cookie_clears_on_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
    test_db,
) -> None:
    sess: dict[str, object] = {}
    monkeypatch.setattr(profile_session.st, "session_state", sess)
    monkeypatch.setattr(
        profile_session,
        "_read_session_token_from_cookies",
        lambda: "bogus-token",
    )
    cleared = []
    monkeypatch.setattr(
        profile_session,
        "clear_session_token_cookie",
        lambda: cleared.append(True),
    )
    profile_session.restore_active_profile_from_cookie_if_needed()
    assert ACTIVE_PROFILE_SESSION_KEY not in sess
    assert cleared == [True]


def test_peek_session_token_from_context_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies = SimpleNamespace(
        to_dict=lambda: {profile_session.SESSION_TOKEN_COOKIE_NAME: "  tok123  "},
    )
    monkeypatch.setattr(
        profile_session.st,
        "context",
        SimpleNamespace(cookies=cookies),
    )
    assert profile_session.peek_session_token_from_context_cookies() == "tok123"


def test_peek_session_token_from_context_cookies_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies = SimpleNamespace(to_dict=lambda: {})
    monkeypatch.setattr(
        profile_session.st,
        "context",
        SimpleNamespace(cookies=cookies),
    )
    assert profile_session.peek_session_token_from_context_cookies() is None
