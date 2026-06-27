"""Lookup-key helpers for artist image batch requests."""

from __future__ import annotations

NAME_LOOKUP_PREFIX = "name:"


def artist_image_lookup_key(
    artist_mbid: str | None,
    *,
    artist_name: str | None = None,
) -> str:
    """Build a stable lookup key for one batch artist request."""
    mbid = (artist_mbid or "").strip()
    if mbid:
        return mbid
    name = (artist_name or "").strip().casefold()
    if not name:
        return ""
    return f"{NAME_LOOKUP_PREFIX}{name}"


def is_name_lookup_key(lookup_key: str) -> bool:
    """Return whether a lookup key refers to a name-only request."""
    return lookup_key.startswith(NAME_LOOKUP_PREFIX)
