"""Read access for artist genre profile artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from music_review.data_access.paths import artist_genres_path


def load_artist_genre_profiles(
    path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load artist genre profiles from ``artist_genres.json``.

    Returns an empty dict if the file is missing or invalid.
    """
    p = Path(path) if path is not None else artist_genres_path()
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value
        for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }
