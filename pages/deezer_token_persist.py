"""Deezer OAuth token: Streamlit session + SQLite persistence for logged-in users.

Mirrors :mod:`pages.spotify_token_persist`. Deezer tokens are simpler than
Spotify's: there is no refresh token and tokens issued with the
``offline_access`` permission never expire. The persisted JSON shape captures
``access_token``, ``expires_in`` (seconds; ``0`` means "no expiry"), and the
``obtained_at`` UTC timestamp.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import streamlit as st

from music_review.dashboard.deezer_oauth_token_json import (
    deezer_token_from_json_str,
    deezer_token_to_json_str,
)
from music_review.dashboard.user_db import (
    clear_deezer_oauth_token,
    get_connection,
    load_deezer_oauth_token_json,
    save_deezer_oauth_token,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.deezer_client import DeezerToken

DEEZER_TOKEN_SESSION_KEY = "deezer_token"


def _query_param_first(key: str) -> str | None:
    """Return a single string for a query param (Streamlit may use str or list)."""
    raw = st.query_params.get(key)
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        return str(raw[0]).strip() or None
    s = str(raw).strip()
    return s or None


def _active_user_slug() -> str | None:
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return normalize_profile_slug(raw)
    except ValueError:
        return None


def read_deezer_token_from_session() -> DeezerToken | None:
    """Return a :class:`DeezerToken` from session state, or None."""
    raw = st.session_state.get(DEEZER_TOKEN_SESSION_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        obtained = raw["obtained_at"]
        if isinstance(obtained, str):
            obt_str = obtained
            if obt_str.endswith("Z"):
                obt_str = obt_str[:-1] + "+00:00"
            obtained_at = datetime.fromisoformat(obt_str)
            if obtained_at.tzinfo is None:
                obtained_at = obtained_at.replace(tzinfo=UTC)
        elif isinstance(obtained, datetime):
            obtained_at = obtained
        else:
            return None
        return DeezerToken(
            access_token=str(raw["access_token"]),
            expires_in=int(raw.get("expires_in", 0)),
            obtained_at=obtained_at,
        )
    except Exception:
        return None


def persist_deezer_token(token: DeezerToken) -> None:
    """Write token to session and, when a profile is active, to the user row."""
    st.session_state[DEEZER_TOKEN_SESSION_KEY] = asdict(token)
    slug = _active_user_slug()
    if slug is None:
        return
    conn = get_connection()
    save_deezer_oauth_token(conn, slug, deezer_token_to_json_str(token))


def hydrate_deezer_token_from_db_for_active_user() -> bool:
    """Load token from DB into session when session is empty and profile is set.

    Skips when OAuth callback query params are present (code exchange will
    set a fresh token shortly).

    Returns ``True`` when a token was hydrated into the session.
    """
    if read_deezer_token_from_session() is not None:
        return False
    code = _query_param_first("code")
    state = _query_param_first("state")
    if code and state:
        return False
    slug = _active_user_slug()
    if slug is None:
        return False
    conn = get_connection()
    blob = load_deezer_oauth_token_json(conn, slug)
    if not blob:
        return False
    token = deezer_token_from_json_str(blob)
    if token is None:
        return False
    st.session_state[DEEZER_TOKEN_SESSION_KEY] = asdict(token)
    return True


def clear_persisted_deezer_token_for_active_user() -> None:
    """Remove token from session and from DB for the active profile."""
    st.session_state.pop(DEEZER_TOKEN_SESSION_KEY, None)
    slug = _active_user_slug()
    if slug is None:
        return
    conn = get_connection()
    clear_deezer_oauth_token(conn, slug)
