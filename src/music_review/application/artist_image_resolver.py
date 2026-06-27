"""Resolve artist images via MusicBrainz, Wikidata, and Wikimedia Commons."""

from __future__ import annotations

import logging

from music_review.application.artist_image_attribution import (
    commons_image_to_record_fields,
)
from music_review.application.artist_image_models import (
    ArtistImageRecord,
    CommonsImageInfo,
    utc_now_iso,
)
from music_review.pipeline.enrichment.commons_client import (
    fetch_commons_image_info,
    find_commons_image_by_artist_name,
)
from music_review.pipeline.enrichment.musicbrainz_client import (
    fetch_artist_alias_names,
    fetch_artist_disambiguation,
    fetch_artist_info,
    fetch_artist_wikidata_id,
)
from music_review.pipeline.enrichment.wikidata_client import (
    fetch_commons_filename,
    fetch_wikidata_id_by_musicbrainz_mbid,
)
from music_review.pipeline.enrichment.wikipedia_client import (
    build_wikipedia_search_names,
    find_commons_image_via_wikipedia,
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

    primary = _resolve_via_wikidata(resolved_mbid, resolved_name)
    if primary.status == "ok":
        return primary

    wikipedia_image, wikidata_id = _resolve_via_wikipedia(resolved_mbid, resolved_name)
    if wikipedia_image is not None:
        fields = commons_image_to_record_fields(wikipedia_image)
        logger.info(
            "Resolved Wikipedia fallback for %s (%s): %s",
            resolved_name,
            resolved_mbid,
            wikipedia_image.commons_file,
        )
        return ArtistImageRecord(
            artist_mbid=resolved_mbid,
            artist_name=resolved_name,
            status="ok",
            fetched_at=utc_now_iso(),
            wikidata_id=wikidata_id or primary.wikidata_id,
            **fields,
        )

    commons_image = find_commons_image_by_artist_name(resolved_name)
    if commons_image is not None:
        fields = commons_image_to_record_fields(commons_image)
        logger.info(
            "Resolved Commons search fallback for %s (%s): %s",
            resolved_name,
            resolved_mbid,
            commons_image.commons_file,
        )
        return ArtistImageRecord(
            artist_mbid=resolved_mbid,
            artist_name=resolved_name,
            status="ok",
            fetched_at=utc_now_iso(),
            wikidata_id=primary.wikidata_id,
            **fields,
        )

    return primary


def _resolve_via_wikipedia(
    artist_mbid: str,
    artist_name: str,
) -> tuple[CommonsImageInfo | None, str | None]:
    """Try resolving an image via English Wikipedia article search."""
    disambiguation = fetch_artist_disambiguation(artist_mbid)
    search_names = build_wikipedia_search_names(
        artist_name,
        alias_names=fetch_artist_alias_names(artist_mbid),
        include_the_variants=disambiguation is None,
    )
    return find_commons_image_via_wikipedia(
        search_names,
        disambiguation=disambiguation,
    )


def _resolve_via_wikidata(artist_mbid: str, artist_name: str) -> ArtistImageRecord:
    """Resolve one artist image via Wikidata property P18."""
    wikidata_id = fetch_artist_wikidata_id(artist_mbid)
    if wikidata_id is None:
        wikidata_id = fetch_wikidata_id_by_musicbrainz_mbid(artist_mbid)
    if wikidata_id is None:
        return _not_found_record(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            reason="no_wikidata_id",
        )

    commons_filename = fetch_commons_filename(wikidata_id)
    if commons_filename is None:
        return _not_found_record(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            reason="no_commons_image",
            wikidata_id=wikidata_id,
        )

    commons_info = fetch_commons_image_info(commons_filename)
    if commons_info is None:
        return _not_found_record(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            reason="license_rejected_or_missing_metadata",
            wikidata_id=wikidata_id,
            commons_file=commons_filename,
        )

    fields = commons_image_to_record_fields(commons_info)
    logger.info(
        "Resolved Wikidata image for %s (%s): %s",
        artist_name,
        artist_mbid,
        commons_info.commons_file,
    )
    return ArtistImageRecord(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
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
