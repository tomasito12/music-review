from __future__ import annotations

import importlib
import types

import pytest


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


def test_split_spotify_oauth_callback_state_legacy_token() -> None:
    module = _spotify_playlists_module()
    split = module._split_spotify_oauth_callback_state
    assert split("aB3-xY9_token_only") == ("aB3-xY9_token_only", None)


def test_split_spotify_oauth_callback_state_embeds_profile_slug() -> None:
    module = _spotify_playlists_module()
    split = module._split_spotify_oauth_callback_state
    assert split("csrfpart.my-user_slug") == ("csrfpart", "my-user_slug")


def test_split_spotify_oauth_callback_state_invalid_slug_suffix_is_legacy() -> None:
    module = _spotify_playlists_module()
    split = module._split_spotify_oauth_callback_state
    raw = "csrfpart.!!!"
    assert split(raw) == (raw, None)


def test_spotify_oauth_state_for_authorize_url_appends_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _spotify_playlists_module()
    monkeypatch.setattr(
        module.st,
        "session_state",
        {"active_profile_slug": "demo_user"},
    )
    out = module._spotify_oauth_state_for_authorize_url("csrf123")
    assert out == "csrf123.demo_user"


def test_spotify_oauth_state_for_authorize_url_skips_without_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _spotify_playlists_module()
    monkeypatch.setattr(module.st, "session_state", {})
    assert module._spotify_oauth_state_for_authorize_url("csrf123") == "csrf123"


def test_redirect_uri_mismatch_hint_html_escapes_special_characters() -> None:
    module = _spotify_playlists_module()
    html_fn = module._redirect_uri_mismatch_hint_html
    out = html_fn(
        effective="http://x/?a=1&b=2",
        browser="http://y/<script>",
    )
    assert "<script>" not in out
    assert "&amp;" in out or "1&amp;b" in out
    assert "http://x/" in out
