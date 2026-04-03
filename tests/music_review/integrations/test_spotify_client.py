from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost/callback")
    with pytest.raises(SpotifyConfigError):
        SpotifyAuthConfig.from_env()


def test_spotify_auth_config_from_env_defaults_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "cid")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.delenv("SPOTIFY_SCOPES", raising=False)
    cfg = SpotifyAuthConfig.from_env()
    assert "playlist-modify-public" in cfg.scopes
    assert "playlist-modify-private" in cfg.scopes


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
    mock_resp.text = "bad request"
    mock_post.return_value = mock_resp

    with pytest.raises(RuntimeError):
        client.exchange_code_for_token(code="code123", code_verifier="verifier")


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
        user_id="user1",
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
