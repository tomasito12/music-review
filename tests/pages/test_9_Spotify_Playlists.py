from __future__ import annotations

import importlib
import types


def _spotify_playlists_module() -> types.ModuleType:
    return importlib.import_module("pages.9_Spotify_Playlists")


def test_spotify_page_importable() -> None:
    # Smoke test to ensure the Spotify playlist page can be imported.
    module = _spotify_playlists_module()
    assert hasattr(module, "main")


def test_normalized_spotify_oauth_pending_state_accepts_nonempty_string() -> None:
    module = _spotify_playlists_module()
    norm = module._normalized_spotify_oauth_pending_state
    assert norm("  abc  ") == "abc"


def test_normalized_spotify_oauth_pending_state_rejects_empty_or_non_string() -> None:
    module = _spotify_playlists_module()
    norm = module._normalized_spotify_oauth_pending_state
    assert norm(None) is None
    assert norm("") is None
    assert norm("   ") is None
    assert norm(42) is None


def test_oauth_redirect_urls_equivalent_ignores_trailing_slash() -> None:
    module = _spotify_playlists_module()
    eq = module._oauth_redirect_urls_equivalent
    assert eq(
        "http://127.0.0.1:8501/spotify_playlists",
        "http://127.0.0.1:8501/spotify_playlists/",
    )
    assert eq("  http://x/y  ", "http://x/y")


def test_oauth_redirect_urls_equivalent_detects_path_mismatch() -> None:
    module = _spotify_playlists_module()
    eq = module._oauth_redirect_urls_equivalent
    a = "http://127.0.0.1:8501/"
    b = "http://127.0.0.1:8501/spotify_playlists"
    assert eq(a, b) is False
