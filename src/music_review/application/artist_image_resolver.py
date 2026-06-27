"""Resolve artist images via MusicBrainz, Wikidata, and Wikimedia Commons."""

from __future__ import annotations

import logging

from music_review.application.artist_image_attribution import (
    commons_image_to_record_fields,
)
from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.pipeline.enrichment.commons_client import fetch_commons_image_info
from music_review.pipeline.enrichment.musicbrainz_client import (
    fetch_artist_info,
    fetch_artist_wikidata_id,
)
from music_review.pipeline.enrichment.wikidata_client import (
    fetch_commons_filename,
    fetch_wikidata_id_by_musicbrainz_mbid,
)

logger = logging.getLogger(__name__)


def resolve_artist_image(
    *,
    artist_mbid: str | None = None,
    artist_name: str | None = None,
) -> ArtistImageRecord:
    """Resolve one artist image and return a cacheable record."""
    resolved_mbid, resolved_name = _resolve_artist_identity(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
    )
    if resolved_mbid is None:
        return _not_found_record(
            artist_mbid=artist_mbid or "",
            artist_name=artist_name or "",
            reason="artist_not_found",
        )

    wikidata_id = fetch_artist_wikidata_id(resolved_mbid)
    if wikidata_id is None:
        wikidata_id = fetch_wikidata_id_by_musicbrainz_mbid(resolved_mbid)
    if wikidata_id is None:
        return _not_found_record(
            artist_mbid=resolved_mbid,
            artist_name=resolved_name,
            reason="no_wikidata_id",
        )

    commons_filename = fetch_commons_filename(wikidata_id)
    if commons_filename is None:
        return _not_found_record(
            artist_mbid=resolved_mbid,
            artist_name=resolved_name,
            reason="no_commons_image",
            wikidata_id=wikidata_id,
        )

    commons_info = fetch_commons_image_info(commons_filename)
    if commons_info is None:
        return _not_found_record(
            artist_mbid=resolved_mbid,
            artist_name=resolved_name,
            reason="license_rejected_or_missing_metadata",
            wikidata_id=wikidata_id,
            commons_file=commons_filename,
        )

    fields = commons_image_to_record_fields(commons_info)
    logger.info(
        "Resolved Commons image for %s (%s): %s",
        resolved_name,
        resolved_mbid,
        commons_info.commons_file,
    )
    return ArtistImageRecord(
        artist_mbid=resolved_mbid,
        artist_name=resolved_name,
        status="ok",
        fetched_at=utc_now_iso(),
        wikidata_id=wikidata_id,
        **fields,
    )


def _resolve_artist_identity(
    *,
    artist_mbid: str | None,
    artist_name: str | None,
) -> tuple[str | None, str]:
    """Resolve artist MBID and display name."""
    if artist_mbid:
        return artist_mbid, artist_name or artist_mbid

    if artist_name:
        info = fetch_artist_info(artist_name)
        if info is None:
            return None, artist_name
        return info.mbid, info.name

    return None, ""


def _not_found_record(
    *,
    artist_mbid: str,
    artist_name: str,
    reason: str,
    wikidata_id: str | None = None,
    commons_file: str | None = None,
) -> ArtistImageRecord:
    """Build a negative cache record."""
    return ArtistImageRecord(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        status="not_found",
        fetched_at=utc_now_iso(),
        wikidata_id=wikidata_id,
        commons_file=commons_file,
        reason=reason,
    )
