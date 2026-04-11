"""JSON serialization for persisting :class:`SpotifyToken` in SQLite (per user)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from music_review.integrations.spotify_client import SpotifyToken


def spotify_token_to_json_str(token: SpotifyToken) -> str:
    """Serialize a token for the ``users.spotify_oauth_token_json`` column."""
    payload: dict[str, Any] = {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "expires_at": token.expires_at.isoformat().replace("+00:00", "Z"),
        "refresh_token": token.refresh_token,
        "scope": token.scope,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def spotify_token_from_json_str(raw: str) -> SpotifyToken | None:
    """Parse stored JSON into a :class:`SpotifyToken`, or ``None`` if invalid."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    access = data.get("access_token")
    if not isinstance(access, str) or not access:
        return None
    token_type = data.get("token_type")
    if not isinstance(token_type, str) or not token_type:
        token_type = "Bearer"
    expires_raw = data.get("expires_at")
    if not isinstance(expires_raw, str) or not expires_raw:
        return None
    exp_str = expires_raw
    if exp_str.endswith("Z"):
        exp_str = exp_str[:-1] + "+00:00"
    try:
        expires_at = datetime.fromisoformat(exp_str)
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    rt = data.get("refresh_token")
    refresh_token = rt if isinstance(rt, str) and rt else None
    sc = data.get("scope")
    scope = sc if isinstance(sc, str) and sc else None
    return SpotifyToken(
        access_token=access,
        token_type=token_type,
        expires_at=expires_at,
        refresh_token=refresh_token,
        scope=scope,
    )
