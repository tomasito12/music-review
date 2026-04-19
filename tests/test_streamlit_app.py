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


def test_streaming_verbindungen_page_registered_in_onboarding_navigation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``st.switch_page('pages/3_Streaming_Verbindungen.py')`` must always work.

    The Spotify Playlists page can render its missing-connection callout (with a
    button that calls ``st.switch_page`` to the Streaming-Verbindungen page) in
    sessions where the taste setup is not complete (e.g. fresh OAuth callback).
    Streamlit only allows ``switch_page`` to scripts that are part of the
    currently active ``st.navigation([...])`` list, so the page must be present
    in *both* the onboarding and the full-app navigation.
    """
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: False)

    pages = module._navigation_pages()
    paths = _registered_script_paths(pages)

    assert "pages/3_Streaming_Verbindungen.py" in paths


def test_streaming_verbindungen_page_registered_in_full_app_navigation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Streaming-Verbindungen page must remain available after taste setup."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)

    pages = module._navigation_pages()
    paths = _registered_script_paths(pages)

    assert "pages/3_Streaming_Verbindungen.py" in paths


def test_spotify_playlists_page_registered_in_both_navigations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The OAuth callback URL is stable, so the Spotify page is in both lists."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)

    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: False)
    onboarding_paths = _registered_script_paths(module._navigation_pages())
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)
    full_paths = _registered_script_paths(module._navigation_pages())

    assert "pages/9_Spotify_Playlists.py" in onboarding_paths
    assert "pages/9_Spotify_Playlists.py" in full_paths


def test_deezer_callback_page_registered_in_both_navigations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Deezer OAuth callback URL is stable; the page must be in both lists."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)

    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: False)
    onboarding_paths = _registered_script_paths(module._navigation_pages())
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)
    full_paths = _registered_script_paths(module._navigation_pages())

    assert "pages/10_Deezer_Callback.py" in onboarding_paths
    assert "pages/10_Deezer_Callback.py" in full_paths


def test_playlist_hub_page_registered_in_both_navigations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unified Playlist-Erzeugen hub must be reachable in both nav modes."""
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
    """``playlist_erzeugen`` is the canonical URL slug Spotify/Deezer return to."""
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


def test_deezer_callback_page_uses_stable_url_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Deezer callback page must register the canonical OAuth ``url_path``."""
    module = importlib.import_module("streamlit_app")
    monkeypatch.setattr(module.st, "Page", _PageSpy)
    monkeypatch.setattr(module, "session_taste_setup_complete", lambda: True)

    pages = module._navigation_pages()
    deezer_pages = [
        p
        for p in pages
        if isinstance(p, _PageSpy) and p.src == "pages/10_Deezer_Callback.py"
    ]
    assert len(deezer_pages) == 1
    assert deezer_pages[0].kwargs.get("url_path") == "deezer_callback"
