"""Tests for the shared Spotify connection UI helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from pages import spotify_connection_ui as ui_module

from music_review.dashboard import user_db


def test_active_user_slug_returns_normalized_slug_from_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ACTIVE_PROFILE_SESSION_KEY is the source of truth for who is logged in."""
    monkeypatch.setattr(ui_module.st, "session_state", {"active_profile_slug": "alice"})
    assert ui_module.active_user_slug() == "alice"


def test_active_user_slug_returns_none_for_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui_module.st, "session_state", {})
    assert ui_module.active_user_slug() is None


def test_active_user_slug_returns_none_for_blank_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ui_module.st,
        "session_state",
        {"active_profile_slug": "   "},
    )
    assert ui_module.active_user_slug() is None


def test_user_has_spotify_credentials_false_for_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guests cannot have stored Spotify credentials regardless of DB content."""
    monkeypatch.setattr(ui_module.st, "session_state", {})
    assert ui_module.user_has_spotify_credentials() is False


def test_user_has_spotify_credentials_true_when_db_has_creds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A logged-in user with stored client_id/secret must register as connected."""
    db_path = tmp_path / "creds.db"
    conn = user_db.get_connection(db_path)
    assert user_db.create_user(conn, "alice", "pw12345678")
    user_db.save_spotify_credentials(conn, "alice", "client-id-stored", "secret-stored")

    monkeypatch.setattr(
        ui_module.st,
        "session_state",
        {"active_profile_slug": "alice"},
    )
    monkeypatch.setattr(
        ui_module,
        "get_db_connection",
        lambda: user_db.get_connection(db_path),
    )

    assert ui_module.user_has_spotify_credentials() is True


def test_try_load_user_spotify_config_returns_none_without_creds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "no_creds.db"
    conn = user_db.get_connection(db_path)
    assert user_db.create_user(conn, "alice", "pw12345678")

    monkeypatch.setattr(
        ui_module.st,
        "session_state",
        {"active_profile_slug": "alice"},
    )
    monkeypatch.setattr(
        ui_module,
        "get_db_connection",
        lambda: user_db.get_connection(db_path),
    )

    assert ui_module.try_load_user_spotify_config() is None


def test_render_spotify_login_link_for_streaming_connections_persists_return_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The login link must remember that the user came from the connection page."""
    persisted: list[str] = []
    rendered: list[tuple[object, str]] = []

    def _fake_render(client: object, *, link_label: str = "x") -> None:
        rendered.append((client, link_label))

    monkeypatch.setattr(
        ui_module,
        "persist_spotify_oauth_return_page_cookie",
        lambda value: persisted.append(value),
    )
    monkeypatch.setattr(
        ui_module,
        "render_spotify_login_link_under_preview",
        _fake_render,
    )

    sentinel_client = object()
    ui_module.render_spotify_login_link_for_streaming_connections(
        sentinel_client,  # type: ignore[arg-type]
    )

    assert persisted == [ui_module.SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS]
    assert rendered == [(sentinel_client, "Mit Spotify verbinden")]


def test_render_spotify_login_link_for_streaming_connections_passes_custom_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Callers can override the German label of the authorize link."""
    monkeypatch.setattr(
        ui_module,
        "persist_spotify_oauth_return_page_cookie",
        lambda value: None,
    )
    captured_label: list[str] = []
    monkeypatch.setattr(
        ui_module,
        "render_spotify_login_link_under_preview",
        lambda client, *, link_label="x": captured_label.append(link_label),
    )

    ui_module.render_spotify_login_link_for_streaming_connections(
        object(),  # type: ignore[arg-type]
        link_label="Erneut mit Spotify verbinden",
    )

    assert captured_label == ["Erneut mit Spotify verbinden"]
