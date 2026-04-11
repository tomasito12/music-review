"""Tests for Spotify OAuth token JSON serialization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from music_review.dashboard.spotify_oauth_token_json import (
    spotify_token_from_json_str,
    spotify_token_to_json_str,
)
from music_review.integrations.spotify_client import SpotifyToken


def _sample_token() -> SpotifyToken:
    return SpotifyToken(
        access_token="access-abc",
        token_type="Bearer",
        expires_at=datetime(2030, 1, 15, 12, 0, 0, tzinfo=UTC),
        refresh_token="refresh-xyz",
        scope="user-read-email playlist-modify-private",
    )


def test_spotify_token_json_roundtrip() -> None:
    original = _sample_token()
    blob = spotify_token_to_json_str(original)
    restored = spotify_token_from_json_str(blob)
    assert restored is not None
    assert restored.access_token == original.access_token
    assert restored.token_type == original.token_type
    assert restored.expires_at == original.expires_at
    assert restored.refresh_token == original.refresh_token
    assert restored.scope == original.scope


def test_spotify_token_from_json_rejects_invalid_json() -> None:
    assert spotify_token_from_json_str("{") is None
    assert spotify_token_from_json_str("") is None


def test_spotify_token_from_json_rejects_non_object() -> None:
    assert spotify_token_from_json_str("[]") is None
    assert spotify_token_from_json_str('"string"') is None


def test_spotify_token_from_json_rejects_missing_access_token() -> None:
    assert spotify_token_from_json_str("{}") is None
    assert spotify_token_from_json_str('{"access_token":""}') is None


def test_spotify_token_from_json_accepts_zulu_expires_at() -> None:
    blob = (
        '{"access_token":"a","token_type":"Bearer",'
        '"expires_at":"2030-06-01T00:00:00Z",'
        '"refresh_token":"r","scope":null}'
    )
    t = spotify_token_from_json_str(blob)
    assert t is not None
    assert t.access_token == "a"
    assert t.refresh_token == "r"
    assert t.scope is None
    assert t.expires_at.tzinfo is not None
    assert t.expires_at.year == 2030


def test_spotify_token_roundtrip_preserves_refresh_none() -> None:
    t = SpotifyToken(
        access_token="only-access",
        token_type="Bearer",
        expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
        refresh_token=None,
        scope="user-read-email",
    )
    out = spotify_token_from_json_str(spotify_token_to_json_str(t))
    assert out is not None
    assert out.refresh_token is None
    assert out.scope == "user-read-email"
