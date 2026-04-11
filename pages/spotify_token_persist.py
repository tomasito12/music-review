"""Spotify OAuth token: Streamlit session + SQLite persistence for logged-in users."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import streamlit as st

from music_review.dashboard.spotify_oauth_token_json import (
    spotify_token_from_json_str,
    spotify_token_to_json_str,
)
from music_review.dashboard.user_db import (
    clear_spotify_oauth_token,
    get_connection,
    load_spotify_oauth_token_json,
    save_spotify_oauth_token,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.spotify_client import SpotifyToken

SPOTIFY_TOKEN_SESSION_KEY = "spotify_token"


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


def read_spotify_token_from_session() -> SpotifyToken | None:
    """Return a :class:`SpotifyToken` from session state, or None."""
    raw = st.session_state.get(SPOTIFY_TOKEN_SESSION_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        exp = raw["expires_at"]
        if isinstance(exp, str):
            exp_str = exp
            if exp_str.endswith("Z"):
                exp_str = exp_str[:-1] + "+00:00"
            expires_at = datetime.fromisoformat(exp_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
        elif isinstance(exp, datetime):
            expires_at = exp
        else:
            return None
        return SpotifyToken(
            access_token=str(raw["access_token"]),
            token_type=str(raw.get("token_type", "Bearer")),
            expires_at=expires_at,
            refresh_token=raw.get("refresh_token"),
            scope=raw.get("scope"),
        )
    except Exception:
        return None


def persist_spotify_token(token: SpotifyToken) -> None:
    """Write token to session and, when a profile is active, to the user row."""
    st.session_state[SPOTIFY_TOKEN_SESSION_KEY] = asdict(token)
    slug = _active_user_slug()
    if slug is None:
        return
    conn = get_connection()
    save_spotify_oauth_token(conn, slug, spotify_token_to_json_str(token))


def hydrate_spotify_token_from_db_for_active_user() -> bool:
    """Load token from DB into session if session is empty and profile is set.

    Skips when OAuth callback query params are present (code exchange will set
    a fresh token).

    Returns True when a token was loaded into the session.
    """
    if read_spotify_token_from_session() is not None:
        return False
    code = _query_param_first("code")
    state = _query_param_first("state")
    if code and state:
        return False
    slug = _active_user_slug()
    if slug is None:
        return False
    conn = get_connection()
    blob = load_spotify_oauth_token_json(conn, slug)
    if not blob:
        return False
    token = spotify_token_from_json_str(blob)
    if token is None:
        return False
    st.session_state[SPOTIFY_TOKEN_SESSION_KEY] = asdict(token)
    return True


def clear_persisted_spotify_token_for_active_user() -> None:
    """Remove token from session and from DB for the active profile."""
    st.session_state.pop(SPOTIFY_TOKEN_SESSION_KEY, None)
    slug = _active_user_slug()
    if slug is None:
        return
    conn = get_connection()
    clear_spotify_oauth_token(conn, slug)
