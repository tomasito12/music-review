"""Passwordless user profiles: JSON on disk under data/user_profiles/.

Profiles are identified by a normalized slug (no password). Not suitable for
untrusted multi-tenant deployments.
"""

from __future__ import annotations

import json
import math
import re
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

SCHEMA_VERSION = 1
MAX_SLUG_LEN = 48
# Shared session_state key for signed-in profile (used by Streamlit pages).
ACTIVE_PROFILE_SESSION_KEY = "active_profile_slug"
# Browser cookie for remembering the last profile slug (client persistence).
ACTIVE_PROFILE_COOKIE_NAME = "mr_active_profile_slug"
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Spotify newest-playlist preview: rate limit per profile or guest session.
SPOTIFY_PREVIEW_COOLDOWN_SECONDS = 600
PROFILE_SPOTIFY_LAST_PREVIEW_AT_KEY = "spotify_last_preview_generated_at"
SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY = "spotify_last_preview_generated_at"


class ProfileHydrationResult(Enum):
    """Outcome of syncing session profile fields from on-disk JSON."""

    NO_ACTIVE_SLUG = auto()
    HYDRATED = auto()
    CLEARED_MISSING_PROFILE_FILE = auto()
    CLEARED_INVALID_SLUG = auto()


def default_profiles_dir() -> Path:
    """Directory for profile JSON files (typically gitignored via data/)."""
    return resolve_data_path("data/user_profiles")


def list_profile_slugs(base_dir: Path) -> list[str]:
    """Return sorted slugs of all saved profiles (filenames without .json)."""
    if not base_dir.is_dir():
        return []
    return sorted(p.stem for p in base_dir.glob("*.json") if p.is_file())


def normalize_profile_slug(raw: str) -> str:
    """Normalize user input to a safe filename component.

    Leading and trailing space is stripped. Any remaining whitespace
    (spaces, tabs, line breaks inside the name) is rejected so users
    are asked to omit spaces rather than having them stripped silently.

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


def profile_file_path(base_dir: Path, slug: str) -> Path:
    """Return path to ``{slug}.json`` under base_dir."""
    safe = normalize_profile_slug(slug)
    return base_dir / f"{safe}.json"


def load_profile(base_dir: Path, slug: str) -> dict[str, Any] | None:
    """Load profile JSON or None if missing."""
    path = profile_file_path(base_dir, slug)
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def save_profile(base_dir: Path, slug: str, payload: dict[str, Any]) -> None:
    """Write profile atomically (temp file + replace)."""
    base_dir.mkdir(parents=True, exist_ok=True)
    path = profile_file_path(base_dir, slug)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_iso_datetime_utc(raw: Any) -> datetime | None:
    """Parse ISO-8601 timestamps from profile JSON; return timezone-aware UTC."""
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
    """Last preview time: from active profile JSON if signed in, else session only."""
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(raw_slug, str) and raw_slug.strip():
        try:
            slug = normalize_profile_slug(raw_slug.strip())
        except ValueError:
            return parse_iso_datetime_utc(
                session.get(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY),
            )
        prof = load_profile(profiles_dir, slug)
        dt = read_last_spotify_preview_at_from_profile(prof)
        if dt is not None:
            return dt
        return None
    return parse_iso_datetime_utc(session.get(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY))


def record_spotify_preview_generated(
    *,
    session: MutableMapping[str, Any],
    profiles_dir: Path,
    when_utc: datetime,
) -> None:
    """Persist preview timestamp to profile JSON or guest session_state."""
    when = when_utc if when_utc.tzinfo else when_utc.replace(tzinfo=UTC)
    iso = when.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if isinstance(raw_slug, str) and raw_slug.strip():
        try:
            slug = normalize_profile_slug(raw_slug.strip())
        except ValueError:
            session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso
            return
        data = load_profile(profiles_dir, slug)
        if not isinstance(data, dict):
            session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso
            return
        merged = dict(data)
        merged[PROFILE_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso
        save_profile(profiles_dir, slug, merged)
        session.pop(SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY, None)
        return
    session[SESSION_SPOTIFY_LAST_PREVIEW_AT_KEY] = iso


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
    """Build versioned document for persistence.

    Uses the unified ``selected_communities`` key if provided; falls back
    to the legacy ``artist_communities`` / ``genre_communities`` pair.
    Both legacy fields are still written for backward compatibility.
    """
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
        .replace(
            "+00:00",
            "Z",
        ),
        "flow_mode": (
            flow_mode if flow_mode is None or isinstance(flow_mode, str) else None
        ),
        "selected_communities": sel_list,
        "artist_flow_selected_communities": artist_list,
        "genre_flow_selected_communities": genre_list,
        "filter_settings": fs,
        "community_weights_raw": w_out,
    }


def apply_profile_to_session(
    session: MutableMapping[str, Any],
    data: Mapping[str, Any],
) -> None:
    """Apply loaded profile dict to a session-like mapping.

    Reads the unified ``selected_communities`` field if present;
    falls back to the legacy artist + genre pair for old profiles.
    """
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


def ensure_active_profile_hydrated(
    session: MutableMapping[str, Any],
    *,
    profiles_dir: Path | None = None,
) -> ProfileHydrationResult:
    """Re-load profile JSON into the session when ``ACTIVE_PROFILE_SESSION_KEY`` is set.

    Keeps communities, filters, and weights in sync with disk on every page run so a
    partial ``session_state`` loss (multipage navigation) does not leave the user
    signed in with empty preferences.

    While ``taste_wizard_reset_pending`` is set (after "Filter und Stile
    zurücksetzen"), disk is not applied so the cleared wizard session is not
    immediately overwritten by the saved profile.

    Returns:
        What happened: no slug, successful hydrate, or slug removed (missing file
        or invalid slug in session).
    """
    raw_slug = session.get(ACTIVE_PROFILE_SESSION_KEY)
    if raw_slug is None or not isinstance(raw_slug, str) or not raw_slug.strip():
        return ProfileHydrationResult.NO_ACTIVE_SLUG

    try:
        safe_slug = normalize_profile_slug(raw_slug)
    except ValueError:
        session.pop(ACTIVE_PROFILE_SESSION_KEY, None)
        return ProfileHydrationResult.CLEARED_INVALID_SLUG

    base = profiles_dir if profiles_dir is not None else default_profiles_dir()
    data = load_profile(base, safe_slug)
    if data is None:
        session.pop(ACTIVE_PROFILE_SESSION_KEY, None)
        return ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE

    if safe_slug != raw_slug:
        session[ACTIVE_PROFILE_SESSION_KEY] = safe_slug
    if session.get(TASTE_WIZARD_RESET_PENDING_KEY):
        return ProfileHydrationResult.HYDRATED
    apply_profile_to_session(session, data)
    return ProfileHydrationResult.HYDRATED
