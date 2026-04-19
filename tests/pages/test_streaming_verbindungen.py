"""Tests for the Streaming-Verbindungen page (Spotify and Deezer placeholder)."""

from __future__ import annotations

import importlib
import types

import pytest
from pages import spotify_connection_ui as ui_module


def _streaming_verbindungen_module() -> types.ModuleType:
    return importlib.import_module("pages.3_Streaming_Verbindungen")


def test_streaming_verbindungen_page_importable() -> None:
    """Smoke test: the page module loads and exposes ``main``."""
    module = _streaming_verbindungen_module()
    assert hasattr(module, "main")


def test_render_spotify_section_shows_setup_guide_when_no_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without stored credentials the user must see the setup guide."""
    module = _streaming_verbindungen_module()
    called: list[str] = []
    monkeypatch.setattr(
        module,
        "user_has_spotify_credentials",
        lambda: False,
    )
    monkeypatch.setattr(
        module,
        "render_spotify_setup_guide",
        lambda: called.append("setup_guide"),
    )

    module._render_spotify_section_for_logged_in_user()
    assert called == ["setup_guide"]


def test_render_spotify_section_shows_status_when_token_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a stored token the page shows the connected status, not a login link."""
    module = _streaming_verbindungen_module()
    called: list[str] = []
    monkeypatch.setattr(module, "user_has_spotify_credentials", lambda: True)
    monkeypatch.setattr(
        module,
        "hydrate_spotify_token_from_db_for_active_user",
        lambda: True,
    )
    monkeypatch.setattr(
        module,
        "read_spotify_token_from_session",
        lambda: object(),
    )
    monkeypatch.setattr(
        module,
        "render_spotify_connected_status_and_disconnect",
        lambda: called.append("status"),
    )
    monkeypatch.setattr(
        module,
        "render_spotify_credentials_management",
        lambda: called.append("manage"),
    )

    module._render_spotify_section_for_logged_in_user()
    assert called == ["status", "manage"]


def test_render_spotify_section_shows_login_link_when_creds_but_no_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With creds but no token the page shows the OAuth login link."""
    module = _streaming_verbindungen_module()
    called: list[str] = []
    monkeypatch.setattr(module, "user_has_spotify_credentials", lambda: True)
    monkeypatch.setattr(
        module,
        "hydrate_spotify_token_from_db_for_active_user",
        lambda: True,
    )
    monkeypatch.setattr(module, "read_spotify_token_from_session", lambda: None)
    monkeypatch.setattr(
        module,
        "_build_spotify_client_for_active_user",
        lambda: object(),
    )
    monkeypatch.setattr(
        module,
        "render_spotify_login_link_for_streaming_connections",
        lambda client: called.append("login_link"),
    )
    monkeypatch.setattr(
        module,
        "render_spotify_credentials_management",
        lambda: called.append("manage"),
    )

    module._render_spotify_section_for_logged_in_user()
    assert called == ["login_link", "manage"]


def test_render_spotify_section_shows_error_when_creds_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored creds that fail to load must surface as an actionable error."""
    module = _streaming_verbindungen_module()
    monkeypatch.setattr(module, "user_has_spotify_credentials", lambda: True)
    monkeypatch.setattr(
        module,
        "hydrate_spotify_token_from_db_for_active_user",
        lambda: True,
    )
    monkeypatch.setattr(module, "read_spotify_token_from_session", lambda: None)
    monkeypatch.setattr(module, "_build_spotify_client_for_active_user", lambda: None)
    error_messages: list[str] = []
    monkeypatch.setattr(
        module.st,
        "error",
        lambda msg: error_messages.append(msg),
    )
    monkeypatch.setattr(
        module,
        "render_spotify_credentials_management",
        lambda: None,
    )

    module._render_spotify_section_for_logged_in_user()
    assert any("nicht geladen" in m for m in error_messages)


def test_main_shows_login_required_for_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guests must be told to sign in before configuring Spotify."""
    module = _streaming_verbindungen_module()
    monkeypatch.setattr(module, "active_user_slug", lambda: None)
    monkeypatch.setattr(module, "inject_recommendation_flow_shell_css", lambda: None)
    monkeypatch.setattr(module, "render_toolbar", lambda key: None)
    monkeypatch.setattr(module, "_render_hero", lambda: None)
    monkeypatch.setattr(module, "_render_spotify_subheader", lambda: None)
    monkeypatch.setattr(module, "_render_deezer_section", lambda: None)
    monkeypatch.setattr(module, "_section_divider", lambda: None)
    called: list[str] = []
    monkeypatch.setattr(
        module,
        "render_login_required_callout",
        lambda: called.append("login_required"),
    )
    monkeypatch.setattr(
        module,
        "_render_spotify_section_for_logged_in_user",
        lambda: called.append("spotify_section"),
    )

    module.main()
    assert called == ["login_required"]


def test_main_renders_spotify_section_when_logged_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A logged-in user goes straight to the Spotify configuration section."""
    module = _streaming_verbindungen_module()
    monkeypatch.setattr(module, "active_user_slug", lambda: "alice")
    monkeypatch.setattr(module, "inject_recommendation_flow_shell_css", lambda: None)
    monkeypatch.setattr(module, "render_toolbar", lambda key: None)
    monkeypatch.setattr(module, "_render_hero", lambda: None)
    monkeypatch.setattr(module, "_render_spotify_subheader", lambda: None)
    monkeypatch.setattr(module, "_render_deezer_section", lambda: None)
    monkeypatch.setattr(module, "_section_divider", lambda: None)
    called: list[str] = []
    monkeypatch.setattr(
        module,
        "render_login_required_callout",
        lambda: called.append("login_required"),
    )
    monkeypatch.setattr(
        module,
        "_render_spotify_section_for_logged_in_user",
        lambda: called.append("spotify_section"),
    )

    module.main()
    assert called == ["spotify_section"]


def test_streaming_verbindungen_uses_shared_connection_helpers() -> None:
    """The page must import the shared spotify_connection_ui helpers (no duplicates)."""
    module = _streaming_verbindungen_module()
    assert module.active_user_slug is ui_module.active_user_slug
    assert module.user_has_spotify_credentials is ui_module.user_has_spotify_credentials
    assert module.render_spotify_setup_guide is ui_module.render_spotify_setup_guide
