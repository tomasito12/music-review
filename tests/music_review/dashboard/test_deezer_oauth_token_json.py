"""Tests for Deezer OAuth token JSON serialization."""

from __future__ import annotations

from datetime import UTC, datetime

from music_review.dashboard.deezer_oauth_token_json import (
    deezer_token_from_json_str,
    deezer_token_to_json_str,
)
from music_review.integrations.deezer_client import DeezerToken


def _sample_token() -> DeezerToken:
    return DeezerToken(
        access_token="acc-abc",
        expires_in=3600,
        obtained_at=datetime(2030, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


def test_deezer_token_json_roundtrip() -> None:
    original = _sample_token()
    blob = deezer_token_to_json_str(original)
    restored = deezer_token_from_json_str(blob)
    assert restored is not None
    assert restored.access_token == original.access_token
    assert restored.expires_in == original.expires_in
    assert restored.obtained_at == original.obtained_at


def test_deezer_token_json_roundtrip_offline_token_zero_expiry() -> None:
    """Tokens issued with ``offline_access`` carry ``expires_in == 0``."""
    original = DeezerToken(
        access_token="offline-acc",
        expires_in=0,
        obtained_at=datetime(2026, 4, 18, 9, 0, 0, tzinfo=UTC),
    )
    blob = deezer_token_to_json_str(original)
    restored = deezer_token_from_json_str(blob)
    assert restored is not None
    assert restored.expires_in == 0
    assert restored.is_expired() is False


def test_deezer_token_from_json_rejects_invalid_json() -> None:
    assert deezer_token_from_json_str("{") is None
    assert deezer_token_from_json_str("") is None


def test_deezer_token_from_json_rejects_non_object() -> None:
    assert deezer_token_from_json_str("[]") is None
    assert deezer_token_from_json_str('"string"') is None


def test_deezer_token_from_json_rejects_missing_access_token() -> None:
    assert deezer_token_from_json_str("{}") is None
    assert (
        deezer_token_from_json_str(
            '{"access_token":"","obtained_at":"2030-01-01T00:00:00Z"}'
        )
        is None
    )


def test_deezer_token_from_json_rejects_missing_obtained_at() -> None:
    assert deezer_token_from_json_str('{"access_token":"a"}') is None


def test_deezer_token_from_json_accepts_zulu_obtained_at() -> None:
    blob = '{"access_token":"a","expires_in":0,"obtained_at":"2030-06-01T00:00:00Z"}'
    t = deezer_token_from_json_str(blob)
    assert t is not None
    assert t.access_token == "a"
    assert t.obtained_at.tzinfo is not None
    assert t.obtained_at.year == 2030


def test_deezer_token_from_json_defaults_invalid_expires_in_to_zero() -> None:
    blob = (
        '{"access_token":"a","expires_in":"oops","obtained_at":"2030-06-01T00:00:00Z"}'
    )
    t = deezer_token_from_json_str(blob)
    assert t is not None
    assert t.expires_in == 0
