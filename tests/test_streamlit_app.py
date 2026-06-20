"""Tests for the top-level Streamlit entry point in :mod:`streamlit_app`."""

from __future__ import annotations

import importlib
from typing import Any

import pytest


class _PageSpy:
    """Recording stand-in for ``st.Page`` capturing the source script path."""

    def __init__(self, src: object, **kwargs: Any) -> None:
        self.src = src
        self.kwargs = kwargs


def _registered_script_paths(pages: list[Any]) -> list[str]:
    """Return only the string sources (file paths) of recorded ``_PageSpy`` items."""
    return [p.src for p in pages if isinstance(p, _PageSpy) and isinstance(p.src, str)]


def test_playlist_hub_page_registered_in_both_navigations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Playlist-Erzeugen hub must be reachable in both nav modes."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)

    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: False)
    onboarding_paths = _registered_script_paths(module._navigation_pages())
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)
    full_paths = _registered_script_paths(module._navigation_pages())

    assert "pages/9_Playlist_Erzeugen.py" in onboarding_paths
    assert "pages/9_Playlist_Erzeugen.py" in full_paths


def test_playlist_hub_page_uses_stable_url_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``playlist_erzeugen`` is the canonical URL slug for the playlist hub."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)

    pages = module._navigation_pages()
    hub_pages = [
        p
        for p in pages
        if isinstance(p, _PageSpy) and p.src == "pages/9_Playlist_Erzeugen.py"
    ]
    assert len(hub_pages) == 1
    assert hub_pages[0].kwargs.get("url_path") == "playlist_erzeugen"


def test_streaming_oauth_pages_not_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy Spotify/Deezer OAuth callback pages are no longer in navigation."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)

    paths = _registered_script_paths(module._navigation_pages())

    assert "pages/9_Spotify_Playlists.py" not in paths
    assert "pages/10_Deezer_Callback.py" not in paths
    assert "pages/3_Streaming_Verbindungen.py" not in paths
