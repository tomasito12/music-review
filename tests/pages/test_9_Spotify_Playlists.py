from __future__ import annotations

import importlib
import types
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from music_review.dashboard import user_db


def _spotify_playlists_module() -> types.ModuleType:
    return importlib.import_module("pages.9_Spotify_Playlists")


def test_spotify_authorization_code_digest_is_stable_and_length() -> None:
    module = _spotify_playlists_module()
    d1 = module._spotify_authorization_code_digest("same-code")
    d2 = module._spotify_authorization_code_digest("same-code")
    assert d1 == d2
    assert len(d1) == 24


def test_spotify_oauth_spent_digests_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _spotify_playlists_module()
    monkeypatch.setattr(module.st, "session_state", {})
    module._spotify_oauth_mark_code_digest_spent("digest_a")
    module._spotify_oauth_mark_code_digest_spent("digest_b")
    assert module._spotify_oauth_spent_digests_list() == ["digest_a", "digest_b"]


def test_spotify_page_importable() -> None:
    # Smoke test to ensure the Spotify playlist page can be imported.
    module = _spotify_playlists_module()
    assert hasattr(module, "main")


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
    kickoff = importlib.import_module("pages.spotify_oauth_kickoff")
    monkeypatch.setattr(
        kickoff.st,
        "session_state",
        {"active_profile_slug": "demo_user"},
    )
    out = kickoff.spotify_oauth_state_for_authorize_url("csrf123")
    assert out == "csrf123.demo_user"


def test_spotify_oauth_state_for_authorize_url_skips_without_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kickoff = importlib.import_module("pages.spotify_oauth_kickoff")
    monkeypatch.setattr(kickoff.st, "session_state", {})
    assert kickoff.spotify_oauth_state_for_authorize_url("csrf123") == "csrf123"


def test_spotify_oauth_session_snapshot_dict_builds_expected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kickoff = importlib.import_module("pages.spotify_oauth_kickoff")
    monkeypatch.setattr(
        kickoff.st,
        "session_state",
        {
            "filter_settings": {"year_min": 2000},
            "community_weights_raw": {"C001": 0.5},
            "selected_communities": {"C001", "C002"},
            "artist_flow_selected_communities": {"C001"},
            "genre_flow_selected_communities": set(),
            "flow_mode": "test",
            "free_text_query": "hello",
            "spotify-page-pool-count": 15,
            "newest-spotify-taste-orientation": "stark",
        },
    )
    d = kickoff.spotify_oauth_session_snapshot_dict()
    assert d["snapshot_version"] == 1
    assert d["filter_settings"]["year_min"] == 2000
    assert d["community_weights_raw"]["C001"] == 0.5
    assert set(d["selected_communities"]) == {"C001", "C002"}
    assert d["genre_flow_selected_communities"] == []
    assert d["widgets"]["spotify-page-pool-count"] == 15
    assert d["widgets"]["newest-spotify-taste-orientation"] == "stark"


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
    assert "127.0.0.1" in out
    assert "localhost" in out


def test_oauth_profile_slug_from_state_param_returns_slug() -> None:
    module = _spotify_playlists_module()
    assert module._oauth_profile_slug_from_state_param("csrf.my-user_slug") == (
        "my-user_slug"
    )


def test_oauth_profile_slug_from_state_param_returns_none_for_legacy_state() -> None:
    module = _spotify_playlists_module()
    assert module._oauth_profile_slug_from_state_param("csrf-token-only") is None


def test_spotify_oauth_callback_query_present_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _spotify_playlists_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "auth-code", "state": "csrf.alice"},
    )
    assert module._spotify_oauth_callback_query_present() is True


def test_spotify_oauth_callback_query_present_false_without_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _spotify_playlists_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"state": "only-state"},
    )
    assert module._spotify_oauth_callback_query_present() is False


def test_maybe_redirect_after_oauth_switches_when_cookie_targets_streaming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A login started on the Streaming-Verbindungen page must return there."""
    module = _spotify_playlists_module()
    cleared: list[bool] = []
    switched: list[str] = []
    monkeypatch.setattr(
        module,
        "peek_spotify_oauth_return_page_cookie",
        lambda: module.SPOTIFY_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    )
    monkeypatch.setattr(
        module,
        "clear_spotify_oauth_return_page_cookie",
        lambda: cleared.append(True),
    )
    monkeypatch.setattr(module.st, "switch_page", lambda path: switched.append(path))

    module._maybe_redirect_after_successful_oauth()

    assert cleared == [True]
    assert switched == ["pages/3_Streaming_Verbindungen.py"]


def test_maybe_redirect_after_oauth_falls_back_to_playlist_hub_without_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a return cookie, the slim callback page forwards to the hub."""
    module = _spotify_playlists_module()
    cleared: list[bool] = []
    switched: list[str] = []
    monkeypatch.setattr(
        module,
        "peek_spotify_oauth_return_page_cookie",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "clear_spotify_oauth_return_page_cookie",
        lambda: cleared.append(True),
    )
    monkeypatch.setattr(module.st, "switch_page", lambda path: switched.append(path))

    module._maybe_redirect_after_successful_oauth()

    assert cleared == [True]
    assert switched == ["pages/9_Playlist_Erzeugen.py"]


def test_maybe_redirect_after_oauth_targets_playlist_hub_via_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A login started on the playlist hub returns to that hub."""
    module = _spotify_playlists_module()
    cleared: list[bool] = []
    switched: list[str] = []
    monkeypatch.setattr(
        module,
        "peek_spotify_oauth_return_page_cookie",
        lambda: module.SPOTIFY_OAUTH_RETURN_PAGE_PLAYLIST_HUB,
    )
    monkeypatch.setattr(
        module,
        "clear_spotify_oauth_return_page_cookie",
        lambda: cleared.append(True),
    )
    monkeypatch.setattr(module.st, "switch_page", lambda path: switched.append(path))

    module._maybe_redirect_after_successful_oauth()

    assert cleared == [True]
    assert switched == ["pages/9_Playlist_Erzeugen.py"]


def test_load_client_uses_db_credentials_for_slug_in_oauth_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OAuth return must use the same Spotify app as authorize (per-user DB creds)."""
    db_path = tmp_path / "plattenradar_test.db"
    conn = user_db.get_connection(db_path)
    assert user_db.create_user(conn, "alice", "pw12345678")
    user_db.save_spotify_credentials(
        conn,
        "alice",
        "cid-from-db-for-alice",
        "secret-from-db-for-alice",
    )

    module = _spotify_playlists_module()

    def _conn():
        return user_db.get_connection(db_path)

    monkeypatch.setattr(module, "get_db_connection", _conn)
    monkeypatch.setenv(
        "SPOTIFY_REDIRECT_URI",
        "http://127.0.0.1:8501/spotify_playlists",
    )
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "unused-in-this-test", "state": "csrfpart.alice"},
    )

    client, _hint = module._load_client_and_redirect_hint()
    assert client is not None
    auth_url = client.build_authorize_url(state="x", code_challenge="y")
    parsed = parse_qs(urlparse(auth_url).query)
    assert parsed.get("client_id") == ["cid-from-db-for-alice"]
