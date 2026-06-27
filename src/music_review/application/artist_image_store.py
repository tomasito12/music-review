"""JSONL persistence for artist image cache entries."""

from __future__ import annotations

import logging
from pathlib import Path

from music_review.application.artist_image_models import ArtistImageRecord
from music_review.io.jsonl import iter_jsonl_objects, write_jsonl

logger = logging.getLogger(__name__)


def load_artist_image_index(path: Path) -> dict[str, ArtistImageRecord]:
    """Load artist image records keyed by MusicBrainz artist ID."""
    records: dict[str, ArtistImageRecord] = {}
    for obj in iter_jsonl_objects(path, log_errors=True):
        record = ArtistImageRecord.from_dict(obj)
        if record.artist_mbid:
            records[record.artist_mbid] = record
    return records


def upsert_artist_image(path: Path, record: ArtistImageRecord) -> None:
    """Insert or replace one artist image record in the JSONL cache."""
    records = load_artist_image_index(path)
    records[record.artist_mbid] = record
    sorted_records = sorted(records.values(), key=_sort_key)
    write_jsonl(path, (item.to_dict() for item in sorted_records))
    logger.info(
        "Stored artist image cache entry for %s (%s)",
        record.artist_name,
        record.status,
    )


def _sort_key(record: ArtistImageRecord) -> tuple[str, str]:
    """Sort records stably by artist name and MBID."""
    return (record.artist_name.casefold(), record.artist_mbid)
