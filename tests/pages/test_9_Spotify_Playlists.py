from __future__ import annotations

import importlib


def test_spotify_page_importable() -> None:
    # Smoke test to ensure the Spotify playlist page can be imported.
    module = importlib.import_module("pages.9_Spotify_Playlists")
    assert hasattr(module, "main")
