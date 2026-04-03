from __future__ import annotations

import importlib


def test_neueste_spotify_playlist_section_importable() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert hasattr(module, "render_neueste_spotify_playlist_section")
