from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from music_review.integrations.spotify_client import (
    SPOTIFY_AUTH_BASE_URL,
    SpotifyArtist,
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyConfigError,
    SpotifyPlaylist,
    SpotifyToken,
    SpotifyTrack,
    generate_pkce_pair,
    normalize_streamlit_spotify_redirect_uri,
    pkce_challenge_from_verifier,
    resolve_spotify_redirect_uri,
)


def _sample_token_payload() -> dict[str, Any]:
    return {
        "access_token": "access123",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "refresh123",
        "scope": "playlist-modify-public playlist-modify-private",
    }


def test_spotify_auth_config_from_env_missing_client_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_SCOPES", raising=False)
    # Do not read the real project .env (it may define Spotify keys).
    (tmp_path / ".env").write_text("# empty for test\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SpotifyConfigError):
        SpotifyAuthConfig.from_env()


class TestFromUserCredentials:
    def test_builds_config_with_explicit_redirect(self) -> None:
        cfg = SpotifyAuthConfig.from_user_credentials(
            client_id="test-id",
            client_secret="test-secret",
            redirect_uri="http://127.0.0.1:8501/spotify_playlists",
        )
        assert cfg.client_id == "test-id"
        assert cfg.client_secret == "test-secret"
        assert cfg.redirect_uri == "http://127.0.0.1:8501/spotify_playlists"
        assert "playlist-modify-public" in cfg.scopes

    def test_falls_back_to_env_redirect_uri(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "SPOTIFY_REDIRECT_URI",
            "http://example.com/spotify_playlists",
        )
        cfg = SpotifyAuthConfig.from_user_credentials(
            client_id="cid",
            client_secret="csec",
        )
        assert cfg.redirect_uri == "http://example.com/spotify_playlists"

    def test_raises_when_empty_client_id(self) -> None:
        with pytest.raises(SpotifyConfigError):
            SpotifyAuthConfig.from_user_credentials(
                client_id="",
                client_secret="sec",
                redirect_uri="http://x/callback",
            )

    def test_raises_when_empty_client_secret(self) -> None:
        with pytest.raises(SpotifyConfigError):
            SpotifyAuthConfig.from_user_credentials(
                client_id="cid",
                client_secret="",
                redirect_uri="http://x/callback",
            )

    def test_raises_when_no_redirect_uri_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)
        with pytest.raises(SpotifyConfigError):
            SpotifyAuthConfig.from_user_credentials(
                client_id="cid",
                client_secret="csec",
            )

    def test_normalizes_redirect_uri_casing(self) -> None:
        cfg = SpotifyAuthConfig.from_user_credentials(
            client_id="cid",
            client_secret="csec",
            redirect_uri="http://host/Spotify_Playlists",
        )
        assert cfg.redirect_uri == "http://host/spotify_playlists"

    def test_custom_scopes(self) -> None:
        cfg = SpotifyAuthConfig.from_user_credentials(
            client_id="cid",
            client_secret="csec",
            redirect_uri="http://x/callback",
            scopes=("user-read-email",),
        )
        assert cfg.scopes == ("user-read-email",)

    def test_trims_whitespace_on_credentials(self) -> None:
        cfg = SpotifyAuthConfig.from_user_credentials(
            client_id="  cid  ",
            client_secret="  csec  ",
            redirect_uri="http://x/callback",
        )
        assert cfg.client_id == "cid"
        assert cfg.client_secret == "csec"


def test_spotify_auth_config_from_env_defaults_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "cid")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.delenv("SPOTIFY_SCOPES", raising=False)
    cfg = SpotifyAuthConfig.from_env()
    assert "playlist-modify-public" in cfg.scopes
    assert "playlist-modify-private" in cfg.scopes


def test_spotify_auth_config_from_env_normalizes_spotify_page_path_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "cid")
    monkeypatch.setenv(
        "SPOTIFY_REDIRECT_URI",
        "http://127.0.0.1:8501/Spotify_Playlists",
    )
    monkeypatch.delenv("SPOTIFY_SCOPES", raising=False)
    cfg = SpotifyAuthConfig.from_env()
    assert cfg.redirect_uri == "http://127.0.0.1:8501/spotify_playlists"


def test_normalize_streamlit_spotify_redirect_uri_fixes_last_segment_case() -> None:
    assert (
        normalize_streamlit_spotify_redirect_uri(
            "http://127.0.0.1:8501/Spotify_Playlists",
        )
        == "http://127.0.0.1:8501/spotify_playlists"
    )


def test_normalize_streamlit_spotify_redirect_uri_leaves_other_paths() -> None:
    uri = "http://127.0.0.1:8501/other/callback"
    assert normalize_streamlit_spotify_redirect_uri(uri) == uri


def test_normalize_spotify_redirect_uri_keeps_query_and_fragment() -> None:
    """Unusual redirect URIs may include query or fragment; keep them."""
    uri = "http://h/Spotify_Playlists?x=1#frag"
    out = normalize_streamlit_spotify_redirect_uri(uri)
    assert "spotify_playlists" in out
    assert "x=1" in out


def test_spotify_token_from_response_sets_expiry() -> None:
    token = SpotifyToken.from_token_response(_sample_token_payload())
    assert token.access_token == "access123"
    assert token.refresh_token == "refresh123"
    assert (token.expires_at - datetime.now(tz=UTC)) > timedelta(seconds=3500)


def test_spotify_token_is_expired_leeway() -> None:
    now = datetime.now(tz=UTC)
    token = SpotifyToken(
        access_token="a",
        token_type="Bearer",
        expires_at=now + timedelta(seconds=10),
        refresh_token=None,
        scope=None,
    )
    assert token.is_expired(leeway_seconds=20) is True
    assert token.is_expired(leeway_seconds=5) is False


def test_generate_pkce_pair_shapes() -> None:
    verifier, challenge = generate_pkce_pair()
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) > 10
    assert "=" not in challenge


def test_resolve_spotify_redirect_uri_uses_configured_despite_browser_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPOTIFY_OAUTH_USE_BROWSER_REDIRECT_URI", raising=False)
    assert (
        resolve_spotify_redirect_uri(
            configured="http://127.0.0.1:8501/cb",
            browser_url="http://localhost:8501/spotify_playlists",
        )
        == "http://127.0.0.1:8501/cb"
    )


def test_resolve_spotify_redirect_uri_uses_browser_when_env_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPOTIFY_OAUTH_USE_BROWSER_REDIRECT_URI", "1")
    assert (
        resolve_spotify_redirect_uri(
            configured="http://127.0.0.1:8501/cb",
            browser_url="http://localhost:8501/spotify_playlists",
        )
        == "http://localhost:8501/spotify_playlists"
    )


def test_resolve_spotify_redirect_uri_falls_back_when_browser_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPOTIFY_OAUTH_USE_BROWSER_REDIRECT_URI", raising=False)
    assert (
        resolve_spotify_redirect_uri(
            configured="  http://127.0.0.1:8501/x  ",
            browser_url=None,
        )
        == "http://127.0.0.1:8501/x"
    )


def test_resolve_spotify_redirect_uri_falls_back_when_browser_not_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPOTIFY_OAUTH_USE_BROWSER_REDIRECT_URI", raising=False)
    assert (
        resolve_spotify_redirect_uri(
            configured="http://a/b",
            browser_url="file:///tmp/x",
        )
        == "http://a/b"
    )


def test_spotify_client_with_redirect_uri_and_property() -> None:
    base = SpotifyClient(
        SpotifyAuthConfig(
            client_id="cid",
            redirect_uri="http://old/cb",
            scopes=("playlist-modify-public",),
        ),
    )
    other = base.with_redirect_uri("http://new/cb")
    assert base.redirect_uri == "http://old/cb"
    assert other.redirect_uri == "http://new/cb"
    url = other.build_authorize_url(state="s")
    assert "redirect_uri=http%3A%2F%2Fnew%2Fcb" in url


def test_spotify_client_with_redirect_uri_rejects_empty() -> None:
    client = SpotifyClient(
        SpotifyAuthConfig(
            client_id="c",
            redirect_uri="http://x",
            scopes=("playlist-modify-public",),
        ),
    )
    with pytest.raises(ValueError, match="redirect_uri"):
        client.with_redirect_uri("  ")


def test_build_authorize_url_contains_expected_query() -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public", "playlist-modify-private"),
    )
    client = SpotifyClient(cfg)
    url = client.build_authorize_url(state="xyz", code_challenge="abc123")
    assert url.startswith(f"{SPOTIFY_AUTH_BASE_URL}/authorize?")
    # Basic sanity checks on query string
    assert "client_id=cid" in url
    assert "state=xyz" in url
    assert "code_challenge=abc123" in url


@patch("music_review.integrations.spotify_client.requests.post")
def test_exchange_code_for_token_success(mock_post: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
        client_secret=None,
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _sample_token_payload()
    mock_post.return_value = mock_resp

    token = client.exchange_code_for_token(code="code123", code_verifier="verifier")
    assert token.access_token == "access123"
    assert mock_post.called


@patch("music_review.integrations.spotify_client.requests.post")
def test_exchange_code_for_token_error_raises(mock_post: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
        client_secret=None,
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error":"invalid_grant","error_description":"code expired"}'
    mock_resp.json.return_value = {
        "error": "invalid_grant",
        "error_description": "code expired",
    }
    mock_post.return_value = mock_resp

    with pytest.raises(RuntimeError, match="invalid_grant"):
        client.exchange_code_for_token(code="code123", code_verifier="verifier")


def test_pkce_challenge_from_verifier_matches_generate_pair() -> None:
    verifier, challenge = generate_pkce_pair()
    assert pkce_challenge_from_verifier(verifier) == challenge


@patch("music_review.integrations.spotify_client.requests.post")
def test_refresh_access_token_preserves_refresh_when_missing(
    mock_post: MagicMock,
) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
        client_secret=None,
    )
    client = SpotifyClient(cfg)
    payload = _sample_token_payload()
    payload.pop("refresh_token", None)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload
    mock_post.return_value = mock_resp

    token = client.refresh_access_token("keep-me")
    assert token.refresh_token == "keep-me"


@patch("music_review.integrations.spotify_client.requests.request")
def test_request_forbidden_includes_spotify_message(mock_req: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.ok = False
    mock_resp.text = '{"error":{"status":403,"message":"Forbidden"}}'
    mock_resp.json.return_value = {"error": {"status": 403, "message": "Forbidden"}}
    mock_req.return_value = mock_resp

    token = SpotifyToken.from_token_response(_sample_token_payload())
    with pytest.raises(RuntimeError, match="Forbidden"):
        client.search_tracks(query="test", limit=5, token=token)


@patch("music_review.integrations.spotify_client.requests.request")
def test_request_unauthorized_raises(mock_req: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
        client_secret=None,
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.ok = False
    mock_resp.text = "unauthorized"
    mock_req.return_value = mock_resp

    token = SpotifyToken.from_token_response(_sample_token_payload())
    with pytest.raises(RuntimeError):
        client.search_tracks(query="test", limit=5, token=token)


@patch("music_review.integrations.spotify_client.requests.request")
def test_search_tracks_maps_fields(mock_req: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "t1",
                    "name": "Song",
                    "uri": "spotify:track:t1",
                    "album": {"name": "Album"},
                    "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
                },
            ],
        },
    }
    mock_req.return_value = mock_resp
    token = SpotifyToken.from_token_response(_sample_token_payload())

    tracks = client.search_tracks(query="Song", limit=10, token=token)
    assert len(tracks) == 1
    t0 = tracks[0]
    assert isinstance(t0, SpotifyTrack)
    assert t0.id == "t1"
    assert t0.album_name == "Album"
    assert t0.artists == ("Artist 1", "Artist 2")


@patch("music_review.integrations.spotify_client.requests.request")
def test_search_artists_maps_fields(mock_req: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
    )
    client = SpotifyClient(cfg)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "artists": {
            "items": [
                {
                    "id": "a1",
                    "name": "Artist",
                    "uri": "spotify:artist:a1",
                },
            ],
        },
    }
    mock_req.return_value = mock_resp
    token = SpotifyToken.from_token_response(_sample_token_payload())

    artists = client.search_artists(query="Artist", limit=5, token=token)
    assert len(artists) == 1
    a0 = artists[0]
    assert isinstance(a0, SpotifyArtist)
    assert a0.id == "a1"
    assert a0.name == "Artist"


@patch("music_review.integrations.spotify_client.requests.request")
def test_create_playlist_and_add_tracks(mock_req: MagicMock) -> None:
    cfg = SpotifyAuthConfig(
        client_id="cid",
        redirect_uri="http://localhost/callback",
        scopes=("playlist-modify-public",),
    )
    client = SpotifyClient(cfg)
    token = SpotifyToken.from_token_response(_sample_token_payload())

    # First call: create playlist
    mock_create = MagicMock()
    mock_create.status_code = 200
    mock_create.ok = True
    mock_create.json.return_value = {
        "id": "pl1",
        "name": "My Playlist",
        "uri": "spotify:playlist:pl1",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"},
    }
    # Second call: add tracks
    mock_add = MagicMock()
    mock_add.status_code = 201
    mock_add.ok = True
    mock_add.json.return_value = {"snapshot_id": "snap"}

    mock_req.side_effect = [mock_create, mock_add]

    playlist = client.create_playlist(
        name="My Playlist",
        public=True,
        token=token,
        description="desc",
    )
    assert isinstance(playlist, SpotifyPlaylist)
    assert playlist.id == "pl1"
    assert playlist.external_url == "https://open.spotify.com/playlist/pl1"

    client.add_tracks_to_playlist(
        playlist_id=playlist.id,
        track_uris=["spotify:track:t1", "spotify:track:t2"],
        token=token,
    )

    assert mock_req.call_count == 2
    create_kw = mock_req.call_args_list[0].kwargs
    assert "/me/playlists" in str(create_kw.get("url", ""))
    add_kw = mock_req.call_args_list[1].kwargs
    add_url = str(add_kw.get("url", ""))
    assert "/playlists/" in add_url
    assert "/items" in add_url
    assert "/tracks" not in add_url
