"""JSON serialization for persisting :class:`DeezerToken` in SQLite (per user)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from music_review.integrations.deezer_client import DeezerToken


def deezer_token_to_json_str(token: DeezerToken) -> str:
    """Serialize a token for the ``users.deezer_oauth_token_json`` column."""
    payload: dict[str, Any] = {
        "access_token": token.access_token,
        "expires_in": int(token.expires_in),
        "obtained_at": token.obtained_at.isoformat().replace("+00:00", "Z"),
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def deezer_token_from_json_str(raw: str) -> DeezerToken | None:
    """Parse stored JSON into a :class:`DeezerToken`, or ``None`` if invalid."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    access = data.get("access_token")
    if not isinstance(access, str) or not access:
        return None
    expires_raw = data.get("expires_in", 0)
    try:
        expires_in = int(expires_raw)
    except (TypeError, ValueError):
        expires_in = 0
    obtained_raw = data.get("obtained_at")
    if not isinstance(obtained_raw, str) or not obtained_raw:
        return None
    obt_str = obtained_raw
    if obt_str.endswith("Z"):
        obt_str = obt_str[:-1] + "+00:00"
    try:
        obtained_at = datetime.fromisoformat(obt_str)
    except ValueError:
        return None
    if obtained_at.tzinfo is None:
        obtained_at = obtained_at.replace(tzinfo=UTC)
    return DeezerToken(
        access_token=access,
        expires_in=expires_in,
        obtained_at=obtained_at,
    )
