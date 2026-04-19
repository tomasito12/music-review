"""Tests for the unified playlist-creation hub page."""

from __future__ import annotations

import importlib
import types

import pytest


def _hub_module() -> types.ModuleType:
    return importlib.import_module("pages.9_Playlist_Erzeugen")


def test_playlist_hub_module_importable() -> None:
    """The unified playlist hub must import cleanly and expose ``main``."""
    module = _hub_module()
    assert hasattr(module, "main")
    assert hasattr(module, "PLAYLIST_HUB_PROVIDER_SESSION_KEY")


def test_resolve_active_provider_defaults_to_spotify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First-time visitors land on Spotify and the choice is recorded in session."""
    module = _hub_module()
    state: dict[str, object] = {}
    monkeypatch.setattr(module.st, "session_state", state)

    chosen = module._resolve_active_provider()

    assert chosen == "Spotify"
    assert state[module.PLAYLIST_HUB_PROVIDER_SESSION_KEY] == "Spotify"


def test_resolve_active_provider_respects_existing_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A previously selected provider must persist across reruns."""
    module = _hub_module()
    state: dict[str, object] = {module.PLAYLIST_HUB_PROVIDER_SESSION_KEY: "Deezer"}
    monkeypatch.setattr(module.st, "session_state", state)

    assert module._resolve_active_provider() == "Deezer"


def test_resolve_active_provider_falls_back_when_value_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garbage in session state must be replaced with the Spotify default."""
    module = _hub_module()
    state: dict[str, object] = {
        module.PLAYLIST_HUB_PROVIDER_SESSION_KEY: "Tidal",
    }
    monkeypatch.setattr(module.st, "session_state", state)

    assert module._resolve_active_provider() == "Spotify"
    assert state[module.PLAYLIST_HUB_PROVIDER_SESSION_KEY] == "Spotify"


def test_render_newest_tab_renders_callout_when_no_reviews(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without reviews the hub explains how to populate ``data/reviews.jsonl``."""
    module = _hub_module()
    monkeypatch.setattr(module, "_render_pool_count_slider", lambda provider: 5)
    monkeypatch.setattr(module, "load_newest_reviews_slice", lambda n: [])

    captured: list[str] = []

    def _fake_callout() -> None:
        captured.append("callout")

    monkeypatch.setattr(module, "_render_no_reviews_callout", _fake_callout)
    spotify_calls: list[object] = []
    monkeypatch.setattr(
        module,
        "render_neueste_spotify_playlist_section",
        lambda **kwargs: spotify_calls.append(kwargs),
    )

    module._render_newest_tab("Spotify")

    assert captured == ["callout"]
    assert spotify_calls == []


def test_render_newest_tab_dispatches_per_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spotify and Deezer each have their own newest-section renderer."""
    module = _hub_module()
    monkeypatch.setattr(module, "_render_pool_count_slider", lambda provider: 5)
    sample_reviews = [{"id": 1}]
    monkeypatch.setattr(
        module,
        "load_newest_reviews_slice",
        lambda n: list(sample_reviews),
    )
    spotify_calls: list[dict[str, object]] = []
    deezer_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "render_neueste_spotify_playlist_section",
        lambda **kwargs: spotify_calls.append(kwargs),
    )
    monkeypatch.setattr(
        module,
        "render_neueste_deezer_playlist_section",
        lambda **kwargs: deezer_calls.append(kwargs),
    )

    module._render_newest_tab("Spotify")
    module._render_newest_tab("Deezer")

    assert len(spotify_calls) == 1
    assert spotify_calls[0]["reviews"] == sample_reviews
    assert len(deezer_calls) == 1
    assert deezer_calls[0]["reviews"] == sample_reviews


def test_render_archive_tab_dispatches_per_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The archive tab forwards the chosen provider to the matching renderer."""
    module = _hub_module()
    spotify_calls: list[bool] = []
    deezer_calls: list[bool] = []
    monkeypatch.setattr(
        module,
        "render_archive_spotify_playlist_section",
        lambda: spotify_calls.append(True),
    )
    monkeypatch.setattr(
        module,
        "render_archive_deezer_playlist_section",
        lambda: deezer_calls.append(True),
    )

    module._render_archive_tab("Spotify")
    module._render_archive_tab("Deezer")

    assert spotify_calls == [True]
    assert deezer_calls == [True]
