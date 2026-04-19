"""Tests for shared Deezer OAuth kick-off helpers."""

from __future__ import annotations

import importlib

import pytest
from pages.deezer_oauth_kickoff import (
    DEEZER_AUTH_STATE_KEY,
    deezer_oauth_session_snapshot_dict,
    deezer_oauth_state_for_authorize_url,
    render_deezer_login_link_under_preview,
    start_deezer_oauth_connection,
)


def test_deezer_oauth_session_snapshot_dict_empty_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    monkeypatch.setattr(module.st, "session_state", {})
    snapshot = deezer_oauth_session_snapshot_dict()
    assert snapshot.get("snapshot_version") == 1
    assert snapshot.get("flow_mode") is None


def test_deezer_oauth_session_snapshot_dict_includes_widgets_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    monkeypatch.setattr(
        module.st,
        "session_state",
        {
            "filter_settings": {"min_score": 8},
            "community_weights_raw": {"C001": 1.0, "C002": 0.5},
            "selected_communities": {"C001"},
            "flow_mode": "neueste",
            "free_text_query": "indie",
            "newest-deezer-playlist-name": "Mix",
            "newest-deezer-song-count": 25,
            "unrelated_widget": "ignored",
        },
    )
    snapshot = deezer_oauth_session_snapshot_dict()
    assert snapshot["filter_settings"] == {"min_score": 8}
    assert snapshot["community_weights_raw"] == {"C001": 1.0, "C002": 0.5}
    assert snapshot["selected_communities"] == ["C001"]
    assert snapshot["flow_mode"] == "neueste"
    assert snapshot["free_text_query"] == "indie"
    assert snapshot["widgets"] == {
        "newest-deezer-playlist-name": "Mix",
        "newest-deezer-song-count": 25,
    }


def test_start_deezer_oauth_connection_sets_state_and_calls_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    calls: list[str] = []

    def _snap() -> None:
        calls.append("snapshot")

    def _state(s: str) -> None:
        calls.append(f"state:{len(s)}")

    monkeypatch.setattr(module, "persist_deezer_oauth_session_snapshot", _snap)
    monkeypatch.setattr(module, "persist_deezer_oauth_state_cookie", _state)
    monkeypatch.setattr(module.st, "session_state", {})

    start_deezer_oauth_connection()

    assert calls[0] == "snapshot"
    assert DEEZER_AUTH_STATE_KEY in module.st.session_state
    assert isinstance(module.st.session_state[DEEZER_AUTH_STATE_KEY], str)
    assert len(calls) == 2
    assert calls[1].startswith("state:")


def test_deezer_oauth_state_for_authorize_url_without_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    monkeypatch.setattr(module.st, "session_state", {})
    assert deezer_oauth_state_for_authorize_url("csrf-1") == "csrf-1"


def test_deezer_oauth_state_for_authorize_url_with_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    monkeypatch.setattr(
        module.st,
        "session_state",
        {module.ACTIVE_PROFILE_SESSION_KEY: "Jamie Doe"},
    )
    monkeypatch.setattr(module, "normalize_profile_slug", lambda s: s.replace(" ", "_"))
    assert deezer_oauth_state_for_authorize_url("csrf-2") == "csrf-2.Jamie_Doe"


def test_render_deezer_login_link_under_preview_shows_authorize_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Renders a single link_button with the URL from the Deezer client."""
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    captured: dict[str, object] = {}

    def _link_button(label: str, url: str, **_kwargs: object) -> None:
        captured["label"] = label
        captured["url"] = url

    monkeypatch.setattr(module.st, "link_button", _link_button)
    monkeypatch.setattr(
        module.st,
        "session_state",
        {DEEZER_AUTH_STATE_KEY: "csrf-raw"},
    )
    monkeypatch.setattr(
        module,
        "deezer_oauth_state_for_authorize_url",
        lambda s: f"state-for-url:{s}",
    )

    class _FakeClient:
        def build_authorize_url(self, *, state: str) -> str:
            return f"https://connect.deezer.com/oauth/auth.php?state={state}"

    render_deezer_login_link_under_preview(_FakeClient())  # type: ignore[arg-type]
    assert captured["label"] == "Verbindung mit Deezer herstellen"
    assert captured["url"] == (
        "https://connect.deezer.com/oauth/auth.php?state=state-for-url:csrf-raw"
    )


def test_render_deezer_login_link_under_preview_calls_start_when_state_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When auth state is absent, kick-off runs so the link can be built."""
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    starts: list[int] = []

    def _start() -> None:
        starts.append(1)
        module.st.session_state[DEEZER_AUTH_STATE_KEY] = "after-start"

    monkeypatch.setattr(module, "start_deezer_oauth_connection", _start)
    monkeypatch.setattr(module.st, "link_button", lambda *a, **k: None)
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "deezer_oauth_state_for_authorize_url",
        lambda s: s,
    )

    class _FakeClient:
        def build_authorize_url(self, *, state: str) -> str:
            return f"https://example/?s={state}"

    render_deezer_login_link_under_preview(_FakeClient())  # type: ignore[arg-type]
    assert starts == [1]


def test_render_deezer_login_link_under_preview_custom_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.deezer_oauth_kickoff")
    captured: dict[str, object] = {}

    def _link_button(label: str, url: str, **_kwargs: object) -> None:
        captured["label"] = label

    monkeypatch.setattr(module.st, "link_button", _link_button)
    monkeypatch.setattr(
        module.st,
        "session_state",
        {DEEZER_AUTH_STATE_KEY: "csrf"},
    )
    monkeypatch.setattr(module, "deezer_oauth_state_for_authorize_url", lambda s: s)

    class _FakeClient:
        def build_authorize_url(self, *, state: str) -> str:
            return f"https://example/?s={state}"

    render_deezer_login_link_under_preview(
        _FakeClient(),  # type: ignore[arg-type]
        link_label="Custom Deezer label",
    )
    assert captured["label"] == "Custom Deezer label"
