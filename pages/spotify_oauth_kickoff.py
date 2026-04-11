"""Shared Spotify OAuth PKCE helpers for the Streamlit Spotify playlist page.

Prepares PKCE/state/cookies and renders the authorize ``link_button`` inline
under the playlist preview controls when no token is stored.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import streamlit as st
from pages.page_helpers import (
    peek_spotify_pkce_verifier_cookie,
    peek_spotify_pkce_verifier_from_context_cookies,
    persist_spotify_oauth_state_cookie,
    persist_spotify_pkce_verifier_cookie,
    persist_spotify_session_snapshot_cookie,
)

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.spotify_client import (
    SpotifyClient,
    generate_pkce_pair,
    pkce_challenge_from_verifier,
)

# Session keys (must match Spotify playlist page consumers).
SPOTIFY_AUTH_STATE_KEY = "spotify_auth_state"
SPOTIFY_PKCE_VERIFIER_KEY = "spotify_pkce_verifier"

# Widget session keys to preserve across Spotify OAuth redirect (cookie snapshot).
_SPOTIFY_OAUTH_SNAPSHOT_WIDGET_KEYS: tuple[str, ...] = (
    "spotify-page-pool-count",
    "newest-spotify-taste-orientation",
    "newest-spotify-playlist-name",
    "newest-spotify-playlist-public",
    "newest-spotify-song-count",
)


def spotify_oauth_session_snapshot_dict() -> dict[str, Any]:
    """Collect taste/filter state from the current session for OAuth round-trip."""
    out: dict[str, Any] = {"snapshot_version": 1}
    fs = st.session_state.get("filter_settings")
    if isinstance(fs, dict):
        out["filter_settings"] = dict(fs)
    cw = st.session_state.get("community_weights_raw")
    if isinstance(cw, dict):
        out["community_weights_raw"] = {
            str(k): float(v) for k, v in cw.items() if isinstance(v, (int, float))
        }
    for key in (
        "selected_communities",
        "artist_flow_selected_communities",
        "genre_flow_selected_communities",
    ):
        val = st.session_state.get(key)
        if isinstance(val, set):
            out[key] = sorted(str(x) for x in val)
        elif isinstance(val, list):
            out[key] = [str(x) for x in val]
    fm = st.session_state.get("flow_mode")
    if fm is None or isinstance(fm, str):
        out["flow_mode"] = fm
    ft = st.session_state.get("free_text_query")
    if isinstance(ft, str):
        out["free_text_query"] = ft
    widgets: dict[str, bool | int | float | str] = {}
    for wkey in _SPOTIFY_OAUTH_SNAPSHOT_WIDGET_KEYS:
        if wkey not in st.session_state:
            continue
        val = st.session_state[wkey]
        if isinstance(val, (bool, int, float, str)):
            widgets[wkey] = val
    if widgets:
        out["widgets"] = widgets
    return out


def persist_spotify_oauth_session_snapshot() -> None:
    """Persist snapshot in a short-lived cookie (browser outlives server session)."""
    payload = spotify_oauth_session_snapshot_dict()
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def _utf8_fits(blob: str, limit: int = 3900) -> bool:
        return len(blob.encode("utf-8")) <= limit

    if not _utf8_fits(raw):
        payload.pop("widgets", None)
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if not _utf8_fits(raw):
        return
    persist_spotify_session_snapshot_cookie(raw)


def start_spotify_pkce_oauth_connection() -> None:
    """Begin PKCE OAuth: snapshot cookie, CSRF state, verifier, and browser cookies."""
    persist_spotify_oauth_session_snapshot()
    state = secrets.token_urlsafe(32)
    pkce_verifier, _ = generate_pkce_pair()
    st.session_state[SPOTIFY_AUTH_STATE_KEY] = state
    st.session_state[SPOTIFY_PKCE_VERIFIER_KEY] = pkce_verifier
    persist_spotify_oauth_state_cookie(state)
    persist_spotify_pkce_verifier_cookie(pkce_verifier)


def spotify_pkce_verifier_raw() -> str | None:
    """Return PKCE verifier from session or browser cookies (OAuth return path)."""
    raw = st.session_state.get(SPOTIFY_PKCE_VERIFIER_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return (
        peek_spotify_pkce_verifier_from_context_cookies()
        or peek_spotify_pkce_verifier_cookie()
    )


def spotify_oauth_code_challenge_for_authorize() -> str | None:
    """Return S256 challenge for the authorize URL, or None if verifier is missing."""
    ver = spotify_pkce_verifier_raw()
    return pkce_challenge_from_verifier(ver) if ver else None


def spotify_oauth_state_for_authorize_url(csrf: str) -> str:
    """Build ``state`` query value: CSRF plus profile slug when logged in."""
    slug_any = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(slug_any, str) or not slug_any.strip():
        return csrf
    try:
        safe = normalize_profile_slug(slug_any.strip())
    except ValueError:
        return csrf
    return f"{csrf}.{safe}"


def render_spotify_login_link_under_preview(
    client: SpotifyClient,
    *,
    link_label: str = "Verbindung mit Spotify herstellen",
) -> None:
    """Show a single Spotify authorize ``link_button`` (no extra captions).

    Omits ``key=`` because some installed Streamlit versions reject it for
    ``st.link_button``.
    """
    raw_state = st.session_state.get(SPOTIFY_AUTH_STATE_KEY)
    if not isinstance(raw_state, str) or not raw_state.strip():
        start_spotify_pkce_oauth_connection()
        raw_state = st.session_state.get(SPOTIFY_AUTH_STATE_KEY)
    if not isinstance(raw_state, str) or not raw_state.strip():
        return
    challenge = spotify_oauth_code_challenge_for_authorize()
    if not challenge:
        st.error(
            "OAuth-Daten sind unvollständig (PKCE fehlt). Bitte die Seite neu laden "
            "und erneut versuchen."
        )
        return
    url = client.build_authorize_url(
        state=spotify_oauth_state_for_authorize_url(raw_state.strip()),
        code_challenge=challenge,
    )
    st.link_button(
        link_label,
        url,
        use_container_width=True,
    )
