"""Passwordless user profiles: JSON on disk under data/user_profiles/.

Profiles are identified by a normalized slug (no password). Not suitable for
untrusted multi-tenant deployments.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from music_review.config import resolve_data_path

SCHEMA_VERSION = 1
MAX_SLUG_LEN = 48
# Shared session_state key for signed-in profile (used by Streamlit pages).
ACTIVE_PROFILE_SESSION_KEY = "active_profile_slug"
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def default_profiles_dir() -> Path:
    """Directory for profile JSON files (typically gitignored via data/)."""
    return resolve_data_path("data/user_profiles")


def normalize_profile_slug(raw: str) -> str:
    """Normalize user input to a safe filename component.

    Raises:
        ValueError: if empty or invalid after normalization.
    """
    s = raw.strip().lower().replace(" ", "-")
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
    artist_communities: set[str] | list[str] | None,
    genre_communities: set[str] | list[str] | None,
    filter_settings: Mapping[str, Any] | None,
    community_weights_raw: Mapping[str, float] | None,
) -> dict[str, Any]:
    """Build versioned document for persistence."""
    artist_list = _sorted_community_list(artist_communities)
    genre_list = _sorted_community_list(genre_communities)

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
        "artist_flow_selected_communities": artist_list,
        "genre_flow_selected_communities": genre_list,
        "filter_settings": fs,
        "community_weights_raw": w_out,
    }


def apply_profile_to_session(
    session: MutableMapping[str, Any],
    data: Mapping[str, Any],
) -> None:
    """Apply loaded profile dict to a session-like mapping (e.g. st.session_state)."""
    artist = data.get("artist_flow_selected_communities")
    if isinstance(artist, list):
        session["artist_flow_selected_communities"] = {str(x) for x in artist}

    genre = data.get("genre_flow_selected_communities")
    if isinstance(genre, list):
        session["genre_flow_selected_communities"] = {str(x) for x in genre}

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
