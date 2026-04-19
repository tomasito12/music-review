"""Shared Deezer OAuth helpers for the Streamlit Deezer playlist flow.

Mirror of :mod:`pages.spotify_oauth_kickoff` adapted to Deezer's quirks:

* Deezer does not use PKCE; only a CSRF ``state`` cookie/session key is needed.
* The CSRF ``state`` value embeds the active profile slug after a ``.``
  separator so the callback page can recover the user even when the server
  session was lost.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

import streamlit as st
from pages.page_helpers import (
    persist_deezer_oauth_state_cookie,
    persist_deezer_session_snapshot_cookie,
)

from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    normalize_profile_slug,
)
from music_review.integrations.deezer_client import DeezerClient

DEEZER_AUTH_STATE_KEY = "deezer_auth_state"

# Widget session keys to preserve across Deezer OAuth redirect (cookie snapshot).
_DEEZER_OAUTH_SNAPSHOT_WIDGET_KEYS: tuple[str, ...] = (
    "deezer-page-pool-count",
    "newest-deezer-taste-orientation",
    "newest-deezer-playlist-name",
    "newest-deezer-playlist-public",
    "newest-deezer-song-count",
)


def deezer_oauth_session_snapshot_dict() -> dict[str, Any]:
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
    for wkey in _DEEZER_OAUTH_SNAPSHOT_WIDGET_KEYS:
        if wkey not in st.session_state:
            continue
        val = st.session_state[wkey]
        if isinstance(val, (bool, int, float, str)):
            widgets[wkey] = val
    if widgets:
        out["widgets"] = widgets
    return out


def persist_deezer_oauth_session_snapshot() -> None:
    """Persist snapshot in a short-lived cookie (browser outlives server session)."""
    payload = deezer_oauth_session_snapshot_dict()
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def _utf8_fits(blob: str, limit: int = 3900) -> bool:
        return len(blob.encode("utf-8")) <= limit

    if not _utf8_fits(raw):
        payload.pop("widgets", None)
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if not _utf8_fits(raw):
        return
    persist_deezer_session_snapshot_cookie(raw)


def start_deezer_oauth_connection() -> None:
    """Begin Deezer OAuth: snapshot cookie, CSRF state, and browser cookies."""
    persist_deezer_oauth_session_snapshot()
    state = secrets.token_urlsafe(32)
    st.session_state[DEEZER_AUTH_STATE_KEY] = state
    persist_deezer_oauth_state_cookie(state)


def deezer_oauth_state_for_authorize_url(csrf: str) -> str:
    """Build ``state`` query value: CSRF plus profile slug when logged in."""
    slug_any = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(slug_any, str) or not slug_any.strip():
        return csrf
    try:
        safe = normalize_profile_slug(slug_any.strip())
    except ValueError:
        return csrf
    return f"{csrf}.{safe}"


def render_deezer_login_link_under_preview(
    client: DeezerClient,
    *,
    link_label: str = "Verbindung mit Deezer herstellen",
) -> None:
    """Show a single Deezer authorize ``link_button`` (no extra captions)."""
    raw_state = st.session_state.get(DEEZER_AUTH_STATE_KEY)
    if not isinstance(raw_state, str) or not raw_state.strip():
        start_deezer_oauth_connection()
        raw_state = st.session_state.get(DEEZER_AUTH_STATE_KEY)
    if not isinstance(raw_state, str) or not raw_state.strip():
        return
    url = client.build_authorize_url(
        state=deezer_oauth_state_for_authorize_url(raw_state.strip()),
    )
    st.link_button(
        link_label,
        url,
        use_container_width=True,
    )
