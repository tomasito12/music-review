"""Tests for shared Spotify OAuth PKCE kick-off helpers."""

from __future__ import annotations

import importlib

import pytest
from pages.spotify_oauth_kickoff import (
    SPOTIFY_AUTH_STATE_KEY,
    SPOTIFY_PKCE_VERIFIER_KEY,
    render_spotify_login_link_under_preview,
    spotify_oauth_session_snapshot_dict,
    start_spotify_pkce_oauth_connection,
)


def test_spotify_oauth_session_snapshot_dict_empty_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.spotify_oauth_kickoff")
    monkeypatch.setattr(module.st, "session_state", {})
    d = spotify_oauth_session_snapshot_dict()
    assert d.get("snapshot_version") == 1
    assert d.get("flow_mode") is None


def test_start_spotify_pkce_oauth_connection_sets_state_and_calls_persist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.spotify_oauth_kickoff")
    calls: list[str] = []

    def _snap() -> None:
        calls.append("snapshot")

    def _state(s: str) -> None:
        calls.append(f"state:{len(s)}")

    def _pkce(v: str) -> None:
        calls.append(f"pkce:{len(v)}")

    monkeypatch.setattr(module, "persist_spotify_oauth_session_snapshot", _snap)
    monkeypatch.setattr(module, "persist_spotify_oauth_state_cookie", _state)
    monkeypatch.setattr(module, "persist_spotify_pkce_verifier_cookie", _pkce)
    monkeypatch.setattr(module.st, "session_state", {})

    start_spotify_pkce_oauth_connection()

    assert calls[0] == "snapshot"
    assert SPOTIFY_AUTH_STATE_KEY in module.st.session_state
    assert SPOTIFY_PKCE_VERIFIER_KEY in module.st.session_state
    assert isinstance(module.st.session_state[SPOTIFY_AUTH_STATE_KEY], str)
    assert isinstance(module.st.session_state[SPOTIFY_PKCE_VERIFIER_KEY], str)
    assert len(calls) == 3
    assert calls[1].startswith("state:")
    assert calls[2].startswith("pkce:")


def test_render_spotify_login_link_under_preview_shows_authorize_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Renders a single link_button with the URL from the Spotify client."""
    module = importlib.import_module("pages.spotify_oauth_kickoff")
    captured: dict[str, object] = {}

    def _link_button(label: str, url: str, **_kwargs: object) -> None:
        captured["label"] = label
        captured["url"] = url

    monkeypatch.setattr(module.st, "link_button", _link_button)
    monkeypatch.setattr(
        module.st,
        "session_state",
        {SPOTIFY_AUTH_STATE_KEY: "csrf-raw"},
    )
    monkeypatch.setattr(
        module,
        "spotify_oauth_code_challenge_for_authorize",
        lambda: "s256-challenge",
    )
    monkeypatch.setattr(
        module,
        "spotify_oauth_state_for_authorize_url",
        lambda s: f"state-for-url:{s}",
    )

    class _FakeClient:
        redirect_uri = "http://127.0.0.1:8501/spotify_playlists"

        def build_authorize_url(self, *, state: str, code_challenge: str) -> str:
            return (
                f"https://accounts.example/authorize?"
                f"state={state}&code_challenge={code_challenge}"
            )

    render_spotify_login_link_under_preview(_FakeClient())
    assert captured["label"] == "Zum Spotify-Login wechseln"
    assert captured["url"] == (
        "https://accounts.example/authorize?"
        "state=state-for-url:csrf-raw&code_challenge=s256-challenge"
    )


def test_render_spotify_login_link_under_preview_calls_start_when_state_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When auth state is absent, kick-off runs so the link can be built."""
    module = importlib.import_module("pages.spotify_oauth_kickoff")
    starts: list[int] = []

    def _start() -> None:
        starts.append(1)
        module.st.session_state[SPOTIFY_AUTH_STATE_KEY] = "after-start"
        module.st.session_state[SPOTIFY_PKCE_VERIFIER_KEY] = "x" * 64

    monkeypatch.setattr(module, "start_spotify_pkce_oauth_connection", _start)
    monkeypatch.setattr(module.st, "link_button", lambda *a, **k: None)
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "spotify_oauth_code_challenge_for_authorize",
        lambda: "challenge",
    )
    monkeypatch.setattr(
        module,
        "spotify_oauth_state_for_authorize_url",
        lambda s: s,
    )

    class _FakeClient:
        redirect_uri = "http://127.0.0.1:8501/spotify_playlists"

        def build_authorize_url(self, *, state: str, code_challenge: str) -> str:
            return f"https://example/?s={state}&cc={code_challenge}"

    render_spotify_login_link_under_preview(_FakeClient())
    assert starts == [1]
