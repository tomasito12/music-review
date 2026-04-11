"""User profiles backed by SQLite (with password authentication).

Public API is kept compatible with the original JSON-file store so that
consumer modules (Streamlit pages) require minimal changes.  Internally
all data lives in ``data/plattenradar.db`` via :mod:`user_db`.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any

from music_review.config import resolve_data_path
from music_review.dashboard.taste_setup import (
    TASTE_WIZARD_RESET_PENDING_KEY,
    clear_taste_wizard_reset_pending,
    data_implies_taste_setup_complete,
    mark_taste_wizard_reset_pending,
)
from music_review.dashboard.user_db import (
    get_connection,
    load_spotify_last_preview_at,
    load_user_profile,
    save_spotify_last_preview_at,
    save_user_profile,
    user_exists,
)

SCHEMA_VERSION = 1
MAX_SLUG_LEN = 48
ACTIVE_PROFILE_SESSION_KEY = "active_profile_slug"
ACTIVE_PROFILE_COOKIE_NAME = "mr_active_profile_slug"
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

SPOTIFY_PREVIEW_COOLDOWN_SECONDS = 600
PROFILE_SPOTIFY_LAST_PREVIEW_AT_KEY = "spotify_last_preview_generated_at"
SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY = "spotify_last_preview_generated_at"


class ProfileHydrationResult(Enum):
    """Outcome of syncing session profile fields from DB."""

    NO_ACTIVE_SLUG = auto()
    HYDRATED = auto()
    CLEARED_MISSING_PROFILE_FILE = auto()
    CLEARED_INVALID_SLUG = auto()


# ---- Slug helpers -----------------------------------------------------------


def normalize_profile_slug(raw: str) -> str:
    """Normalize user input to a safe identifier.

    Raises:
        ValueError: if empty, contains internal whitespace, or invalid.
    """
    s = raw.strip()
    if any(ch.isspace() for ch in s):
        raise ValueError(
            "Bitte verzichte auf Leerzeichen im Profilnamen "
            "(Bindestrich oder Unterstrich sind erlaubt).",
        )
    s = s.lower()
    s = re.sub(r"[^a-z0-9_-]+", "", s)
    s = s.strip("-_")
    if not s:
        raise ValueError("Profilname darf nicht leer sein.")
    if len(s) > MAX_SLUG_LEN:
        raise ValueError(
            f"Profilname maximal {MAX_SLUG_LEN} Zeichen (nach Normalisierung).",
        )
    if not _SLUG_PATTERN.match(s):
        raise ValueError(
            "Profilname nur Kleinbuchstaben, Ziffern, Bindestrich und Unterstrich.",
        )
    return s


# ---- Legacy path helpers (kept for backward compat / tests) -----------------


def default_profiles_dir() -> Path:
    """Return the legacy profiles dir (now used only as a hint)."""
    return resolve_data_path("data/user_profiles")


def profile_file_path(base_dir: Path, slug: str) -> Path:
    """Legacy helper -- returns path under base_dir for the given slug."""
    safe = normalize_profile_slug(slug)
    return base_dir / f"{safe}.json"


def list_profile_slugs(base_dir: Path | None = None) -> list[str]:
    """Return all registered user slugs (from DB)."""
    conn = get_connection()
    from music_review.dashboard.user_db import list_user_slugs

    return list_user_slugs(conn)


# ---- Load / Save (DB-backed) -----------------------------------------------


def _db_conn() -> sqlite3.Connection:
    return get_connection()


def load_profile(
    base_dir: Path,
    slug: str,
) -> dict[str, Any] | None:
    """Load profile data from the database."""
    try:
        safe = normalize_profile_slug(slug)
    except ValueError:
        return None
    conn = _db_conn()
    if not user_exists(conn, safe):
        return None
    data = load_user_profile(conn, safe)
    return data


def save_profile(
    base_dir: Path,
    slug: str,
    payload: dict[str, Any],
) -> None:
    """Persist profile data to the database."""
    safe = normalize_profile_slug(slug)
    conn = _db_conn()
    save_user_profile(conn, safe, payload)


# ---- Timestamp helpers ------------------------------------------------------


def parse_iso_datetime_utc(raw: Any) -> datetime | None:
    """Parse ISO-8601 timestamps; return timezone-aware UTC."""
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def spotify_preview_cooldown_seconds_remaining(
    *,
    now_utc: datetime,
    last_generated_at_utc: datetime | None,
    cooldown_seconds: int = SPOTIFY_PREVIEW_COOLDOWN_SECONDS,
) -> int:
    """Seconds until another Spotify preview; ``0`` means allowed."""
    if last_generated_at_utc is None:
        return 0
    now = now_utc if now_utc.tzinfo else now_utc.replace(tzinfo=UTC)
    last = (
        last_generated_at_utc
        if last_generated_at_utc.tzinfo
        else last_generated_at_utc.replace(tzinfo=UTC)
    )
    deadline = last + timedelta(seconds=cooldown_seconds)
    return max(0, math.ceil((deadline - now).total_seconds()))


def read_last_spotify_preview_at_from_profile(
    data: Mapping[str, Any] | None,
) -> datetime | None:
    """Read last preview timestamp from a loaded profile dict."""
    if not data:
        return None
    return parse_iso_datetime_utc(data.get(PROFILE_SPOTIFY_LAST_PREVIEW_AT_KEY))


def get_spotify_preview_last_generated_at(
    *,
    session: MutableMapping[str, Any],
    profiles_dir: Path,
) -> datetime | None:
    """Last preview time: from DB if signed in, else session only."""
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(raw_slug, str) and raw_slug.strip():
        try:
            slug = normalize_profile_slug(raw_slug.strip())
        except ValueError:
            return parse_iso_datetime_utc(
                session.get(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY),
            )
        conn = _db_conn()
        iso = load_spotify_last_preview_at(conn, slug)
        return parse_iso_datetime_utc(iso)
    return parse_iso_datetime_utc(session.get(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY))


def record_spotify_preview_generated(
    *,
    session: MutableMapping[str, Any],
    profiles_dir: Path,
    when_utc: datetime,
) -> None:
    """Persist preview timestamp to DB or guest session_state."""
    when = when_utc if when_utc.tzinfo else when_utc.replace(tzinfo=UTC)
    iso = when.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(raw_slug, str) and raw_slug.strip():
        try:
            slug = normalize_profile_slug(raw_slug.strip())
        except ValueError:
            session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso
            return
        conn = _db_conn()
        if not user_exists(conn, slug):
            session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso
            return
        save_spotify_last_preview_at(conn, slug, iso)
        session.pop(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY, None)
        return
    session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso


# ---- Profile payload construction ------------------------------------------


def _sorted_community_list(raw: set[str] | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, set):
        return sorted(raw)
    return [str(x) for x in raw]


def build_profile_payload(
    *,
    profile_slug: str,
    flow_mode: Any,
    selected_communities: set[str] | list[str] | None = None,
    artist_communities: set[str] | list[str] | None = None,
    genre_communities: set[str] | list[str] | None = None,
    filter_settings: Mapping[str, Any] | None,
    community_weights_raw: Mapping[str, float] | None,
) -> dict[str, Any]:
    """Build versioned profile document for persistence."""
    sel_list = _sorted_community_list(selected_communities)
    artist_list = _sorted_community_list(artist_communities)
    genre_list = _sorted_community_list(genre_communities)
    if sel_list and not artist_list and not genre_list:
        artist_list = sel_list

    weights = community_weights_raw or {}
    w_out: dict[str, float] = {
        str(k): float(v) for k, v in weights.items() if isinstance(v, (int, float))
    }

    fs = dict(filter_settings) if filter_settings else {}

    return {
        "schema_version": SCHEMA_VERSION,
        "profile_name": normalize_profile_slug(profile_slug),
        "saved_at": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "flow_mode": (
            flow_mode if flow_mode is None or isinstance(flow_mode, str) else None
        ),
        "selected_communities": sel_list,
        "artist_flow_selected_communities": artist_list,
        "genre_flow_selected_communities": genre_list,
        "filter_settings": fs,
        "community_weights_raw": w_out,
    }


# ---- Session application ---------------------------------------------------


def apply_profile_to_session(
    session: MutableMapping[str, Any],
    data: Mapping[str, Any],
) -> None:
    """Apply loaded profile dict to a session-like mapping."""
    sel = data.get("selected_communities")
    if isinstance(sel, list) and sel:
        merged = {str(x) for x in sel}
    else:
        artist = data.get("artist_flow_selected_communities")
        genre = data.get("genre_flow_selected_communities")
        artist_set = {str(x) for x in artist} if isinstance(artist, list) else set()
        genre_set = {str(x) for x in genre} if isinstance(genre, list) else set()
        merged = artist_set | genre_set

    session["selected_communities"] = merged
    session["artist_flow_selected_communities"] = merged
    session["genre_flow_selected_communities"] = set()

    fs = data.get("filter_settings")
    if isinstance(fs, dict):
        session["filter_settings"] = dict(fs)

    weights = data.get("community_weights_raw")
    if isinstance(weights, dict):
        parsed: dict[str, float] = {}
        for k, v in weights.items():
            if isinstance(v, (int, float)):
                parsed[str(k)] = float(v)
        session["community_weights_raw"] = parsed

    fm = data.get("flow_mode")
    if fm is None or isinstance(fm, str):
        session["flow_mode"] = fm

    if data_implies_taste_setup_complete(session):
        clear_taste_wizard_reset_pending(session)
    else:
        mark_taste_wizard_reset_pending(session)


# ---- Hydration from DB on every page run ------------------------------------


def ensure_active_profile_hydrated(
    session: MutableMapping[str, Any],
    *,
    profiles_dir: Path | None = None,
) -> ProfileHydrationResult:
    """Re-load profile from DB when ``ACTIVE_PROFILE_SESSION_KEY`` is set.

    Keeps communities, filters, and weights in sync with the database on
    every page run so a partial ``session_state`` loss does not leave the
    user signed in with empty preferences.
    """
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if raw_slug is None or not isinstance(raw_slug, str) or not raw_slug.strip():
        return ProfileHydrationResult.NO_ACTIVE_SLUG

    try:
        safe_slug = normalize_profile_slug(raw_slug)
    except ValueError:
        session.pop(ACTIVE_PROFILE_SESSION_KEY, None)
        return ProfileHydrationResult.CLEARED_INVALID_SLUG

    conn = _db_conn()
    if not user_exists(conn, safe_slug):
        session.pop(ACTIVE_PROFILE_SESSION_KEY, None)
        return ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE

    if safe_slug != raw_slug:
        session[ACTIVE_PROFILE_SESSION_KEY] = safe_slug

    if session.get(TASTE_WIZARD_RESET_PENDING_KEY):
        return ProfileHydrationResult.HYDRATED

    data = load_user_profile(conn, safe_slug)
    if data is not None:
        apply_profile_to_session(session, data)
    return ProfileHydrationResult.HYDRATED
