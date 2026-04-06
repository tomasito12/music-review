"""Tests for profile cookie helpers (mocked Streamlit cookie manager)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pages import page_helpers

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    build_profile_payload,
    save_profile,
)


def test_persist_active_profile_slug_cookie_skips_invalid_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_cm = MagicMock()
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    page_helpers.persist_active_profile_slug_cookie("!!!")
    mock_cm.set.assert_not_called()


def test_persist_active_profile_slug_cookie_sets_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_cm = MagicMock()
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    page_helpers.persist_active_profile_slug_cookie("Ada")
    mock_cm.set.assert_called_once()
    args, kwargs = mock_cm.set.call_args
    assert args[0] == page_helpers.ACTIVE_PROFILE_COOKIE_NAME
    assert args[1] == "ada"
    assert kwargs.get("same_site") == "lax"


def test_clear_active_profile_slug_cookie_deletes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_cm = MagicMock()
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    page_helpers.clear_active_profile_slug_cookie()
    mock_cm.delete.assert_called_once_with(
        page_helpers.ACTIVE_PROFILE_COOKIE_NAME,
        key="mr_cookie_del_profile",
    )


def test_restore_from_cookie_skips_when_session_has_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sess = {ACTIVE_PROFILE_SESSION_KEY: "ada"}
    monkeypatch.setattr(page_helpers.st, "session_state", sess)
    mock_cm = MagicMock()
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    page_helpers.restore_active_profile_from_cookie_if_needed()
    mock_cm.get.assert_not_called()


def test_restore_from_cookie_hydrates_when_empty_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    payload = build_profile_payload(
        profile_slug="bob",
        flow_mode=None,
        selected_communities={"C01"},
        filter_settings={"x": 1},
        community_weights_raw={"C01": 0.5},
    )
    save_profile(tmp_path, "bob", payload)
    sess: dict[str, object] = {}
    monkeypatch.setattr(page_helpers.st, "session_state", sess)
    mock_cm = MagicMock()
    mock_cm.get.return_value = "bob"
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    monkeypatch.setattr(page_helpers, "default_profiles_dir", lambda: tmp_path)

    page_helpers.restore_active_profile_from_cookie_if_needed()

    assert sess[ACTIVE_PROFILE_SESSION_KEY] == "bob"
    assert sess["selected_communities"] == {"C01"}
    assert sess["filter_settings"] == {"x": 1}


def test_peek_active_profile_slug_from_context_cookies_strips_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies = SimpleNamespace(
        to_dict=lambda: {page_helpers.ACTIVE_PROFILE_COOKIE_NAME: "  bob  "},
    )
    monkeypatch.setattr(
        page_helpers.st,
        "context",
        SimpleNamespace(cookies=cookies),
    )
    assert page_helpers.peek_active_profile_slug_from_context_cookies() == "bob"


def test_peek_active_profile_slug_from_context_cookies_empty_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies = SimpleNamespace(to_dict=lambda: {})
    monkeypatch.setattr(
        page_helpers.st,
        "context",
        SimpleNamespace(cookies=cookies),
    )
    assert page_helpers.peek_active_profile_slug_from_context_cookies() is None


def test_restore_from_cookie_uses_context_when_cookie_manager_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = build_profile_payload(
        profile_slug="bob",
        flow_mode=None,
        selected_communities={"C01"},
        filter_settings={"x": 1},
        community_weights_raw={"C01": 0.5},
    )
    save_profile(tmp_path, "bob", payload)
    sess: dict[str, object] = {}
    monkeypatch.setattr(page_helpers.st, "session_state", sess)
    mock_cm = MagicMock()
    mock_cm.get.return_value = None
    monkeypatch.setattr(
        page_helpers,
        "profile_cookie_manager",
        lambda: mock_cm,
    )
    monkeypatch.setattr(
        page_helpers,
        "peek_active_profile_slug_from_context_cookies",
        lambda: "bob",
    )
    monkeypatch.setattr(page_helpers, "default_profiles_dir", lambda: tmp_path)

    page_helpers.restore_active_profile_from_cookie_if_needed()

    assert sess[ACTIVE_PROFILE_SESSION_KEY] == "bob"
    assert sess["selected_communities"] == {"C01"}
