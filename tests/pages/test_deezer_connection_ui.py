"""Tests for the shared Deezer connection UI helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from pages import deezer_connection_ui as ui_module

from music_review.dashboard import user_db
from music_review.integrations.deezer_client import DeezerAuthConfig


def test_active_user_slug_returns_normalized_slug_from_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ui_module.st,
        "session_state",
        {"active_profile_slug": "alice"},
    )
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


def test_user_has_deezer_credentials_false_for_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui_module.st, "session_state", {})
    assert ui_module.user_has_deezer_credentials() is False


def test_user_has_deezer_credentials_true_when_db_has_creds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "creds.db"
    conn = user_db.get_connection(db_path)
    assert user_db.create_user(conn, "alice", "pw12345678")
    user_db.save_deezer_credentials(conn, "alice", "654321", "secret-stored")

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
    monkeypatch.setenv("DEEZER_REDIRECT_URI", "http://127.0.0.1:8501/deezer_callback")

    assert ui_module.user_has_deezer_credentials() is True


def test_try_load_user_deezer_config_returns_none_without_creds(
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

    assert ui_module.try_load_user_deezer_config() is None


def test_resolve_deezer_auth_config_prefers_user_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """When user has stored credentials, they win over the shared env app."""
    db_path = tmp_path / "creds.db"
    conn = user_db.get_connection(db_path)
    assert user_db.create_user(conn, "alice", "pw12345678")
    user_db.save_deezer_credentials(conn, "alice", "user-app-id", "user-secret")

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
    monkeypatch.setenv("DEEZER_APP_ID", "shared-app-id")
    monkeypatch.setenv("DEEZER_APP_SECRET", "shared-secret")
    monkeypatch.setenv("DEEZER_REDIRECT_URI", "http://127.0.0.1:8501/deezer_callback")

    cfg = ui_module.resolve_deezer_auth_config()
    assert isinstance(cfg, DeezerAuthConfig)
    assert cfg.app_id == "user-app-id"


def test_resolve_deezer_auth_config_falls_back_to_shared_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without per-user credentials the shared project app config is used."""
    monkeypatch.setattr(ui_module.st, "session_state", {})
    monkeypatch.setenv("DEEZER_APP_ID", "shared-app-id")
    monkeypatch.setenv("DEEZER_APP_SECRET", "shared-secret")
    monkeypatch.setenv("DEEZER_REDIRECT_URI", "http://127.0.0.1:8501/deezer_callback")

    cfg = ui_module.resolve_deezer_auth_config()
    assert isinstance(cfg, DeezerAuthConfig)
    assert cfg.app_id == "shared-app-id"


def test_resolve_deezer_auth_config_returns_none_when_nothing_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ui_module.st, "session_state", {})
    monkeypatch.delenv("DEEZER_APP_ID", raising=False)
    monkeypatch.delenv("DEEZER_APP_SECRET", raising=False)
    monkeypatch.delenv("DEEZER_REDIRECT_URI", raising=False)
    monkeypatch.setattr(
        ui_module,
        "try_load_shared_deezer_config",
        lambda: None,
    )

    assert ui_module.resolve_deezer_auth_config() is None


def test_render_deezer_login_link_for_streaming_connections_persists_return_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted: list[str] = []
    rendered: list[tuple[object, str]] = []

    def _fake_render(client: object, *, link_label: str = "x") -> None:
        rendered.append((client, link_label))

    monkeypatch.setattr(
        ui_module,
        "persist_deezer_oauth_return_page_cookie",
        lambda value: persisted.append(value),
    )
    monkeypatch.setattr(
        ui_module,
        "render_deezer_login_link_under_preview",
        _fake_render,
    )

    sentinel_client = object()
    ui_module.render_deezer_login_link_for_streaming_connections(
        sentinel_client,  # type: ignore[arg-type]
    )

    assert persisted == [ui_module.DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS]
    assert rendered == [(sentinel_client, "Mit Deezer verbinden")]


def test_render_deezer_login_link_for_streaming_connections_passes_custom_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ui_module,
        "persist_deezer_oauth_return_page_cookie",
        lambda value: None,
    )
    captured_label: list[str] = []
    monkeypatch.setattr(
        ui_module,
        "render_deezer_login_link_under_preview",
        lambda client, *, link_label="x": captured_label.append(link_label),
    )

    ui_module.render_deezer_login_link_for_streaming_connections(
        object(),  # type: ignore[arg-type]
        link_label="Erneut mit Deezer verbinden",
    )

    assert captured_label == ["Erneut mit Deezer verbinden"]
