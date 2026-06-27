"""Batch and pipeline helpers for artist image caching."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from music_review.application.artist_image_service import ArtistImageService
from music_review.io.jsonl import iter_jsonl_objects

logger = logging.getLogger(__name__)

DEFAULT_FETCH_LIMIT = 25


def unique_artists_from_metadata(
    metadata_path: Path,
) -> list[tuple[str, str]]:
    """Return unique (artist_mbid, artist_name) pairs from metadata JSONL."""
    if not metadata_path.is_file():
        return []

    seen: set[str] = set()
    artists: list[tuple[str, str]] = []
    for obj in iter_jsonl_objects(metadata_path, log_errors=False):
        artist_mbid = obj.get("artist_mbid")
        if not isinstance(artist_mbid, str) or not artist_mbid.strip():
            continue
        mbid = artist_mbid.strip()
        if mbid in seen:
            continue
        seen.add(mbid)
        artist_name = obj.get("artist")
        name = str(artist_name).strip() if artist_name else mbid
        artists.append((mbid, name))
    return artists


def artist_lookup_from_review_metadata(
    metadata: Mapping[int, Mapping[str, Any]],
    review_id: int,
) -> tuple[str | None, str]:
    """Return artist MBID and display name for one review metadata row."""
    row = metadata.get(review_id)
    if row is None:
        return None, ""

    artist_name = row.get("artist")
    name = str(artist_name).strip() if artist_name else ""
    artist_mbid = row.get("artist_mbid")
    if isinstance(artist_mbid, str) and artist_mbid.strip():
        return artist_mbid.strip(), name or artist_mbid.strip()
    return None, name


def fetch_missing_artist_images(
    service: ArtistImageService,
    artists: Iterable[tuple[str, str]],
    *,
    limit: int = DEFAULT_FETCH_LIMIT,
) -> int:
    """Resolve artist images for artists not yet present in cache."""
    resolved_ok = 0
    attempted = 0
    for artist_mbid, artist_name in artists:
        if attempted >= max(1, limit):
            break
        cached = service.cached_record(artist_mbid)
        if cached is not None and (
            cached.status == "ok" or service.is_negative_cache_fresh(cached)
        ):
            continue
        attempted += 1
        record = service.lookup(artist_mbid, artist_name=artist_name or None)
        if record.status == "ok":
            resolved_ok += 1
    logger.info(
        "Fetched %d/%d artist images (%d attempts, limit %d).",
        resolved_ok,
        attempted,
        attempted,
        limit,
    )
    return resolved_ok
