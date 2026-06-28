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
from music_review.pipeline.enrichment.commons_artist_match import (
    musicbrainz_name_matches_requested,
)
from music_review.pipeline.enrichment.commons_client import (
    fetch_commons_image_info,
    find_commons_image_by_artist_name,
)
from music_review.pipeline.enrichment.commons_image_confidence import (
    CURRENT_VALIDATION_VERSION,
    ArtistContext,
    ResolutionSource,
    member_name_eligible_for_fallback,
    score_commons_image_candidate,
    score_parsed_commons_image,
)
from music_review.pipeline.enrichment.musicbrainz_client import (
    fetch_artist_alias_names,
    fetch_artist_disambiguation,
    fetch_artist_info,
    fetch_artist_info_by_mbid,
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
    context: ArtistContext | None = None,
) -> ArtistImageRecord:
    """Resolve one artist image and return a cacheable record."""
    resolved_context = _merge_context(
        context,
        artist_mbid=artist_mbid,
        artist_name=artist_name,
    )
    resolved_mbid, resolved_name = _resolve_artist_identity(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        context=resolved_context,
    )
    if resolved_mbid is not None:
        resolved_context = _with_mbid(resolved_context, resolved_mbid)

    if resolved_mbid is not None:
        primary = _resolve_via_wikidata(
            resolved_mbid,
            resolved_name,
            context=_with_source(resolved_context, "wikidata_p18"),
        )
        if primary.status == "ok":
            return primary
        fallback = _resolve_wikipedia_and_commons_fallbacks(
            resolved_mbid,
            resolved_name,
            wikidata_failure=primary,
            context=resolved_context,
        )
        if fallback.status == "ok":
            return fallback
        return _resolve_member_fallback(
            resolved_mbid,
            resolved_name,
            context=resolved_context,
            prior_failure=fallback,
        )

    if resolved_name:
        fallback = _resolve_wikipedia_and_commons_fallbacks(
            "",
            resolved_name,
            wikidata_failure=None,
            context=_with_source(resolved_context, "commons_search"),
        )
        if fallback.status == "ok":
            return fallback
        return _not_found_record(
            artist_mbid=artist_mbid or "",
            artist_name=resolved_name,
            reason="artist_not_found",
        )

    return _not_found_record(
        artist_mbid=artist_mbid or "",
        artist_name=artist_name or "",
        reason="artist_not_found",
    )


def _merge_context(
    context: ArtistContext | None,
    *,
    artist_mbid: str | None,
    artist_name: str | None,
) -> ArtistContext:
    """Build artist context from explicit values and optional overrides."""
    if context is not None:
        return context
    mbid = (artist_mbid or "").strip() or None
    return ArtistContext(
        artist_mbid=mbid,
        resolution_source="wikidata_p18" if mbid else "commons_search",
    )


def _with_mbid(context: ArtistContext, artist_mbid: str) -> ArtistContext:
    """Return a copy of context with an updated MBID."""
    if context.artist_mbid == artist_mbid:
        return context
    return ArtistContext(
        artist_mbid=artist_mbid,
        artist_type=context.artist_type,
        artist_country=context.artist_country,
        artist_disambiguation=context.artist_disambiguation,
        artist_tags=context.artist_tags,
        main_genres=context.main_genres,
        artist_members=context.artist_members,
        resolution_source=context.resolution_source,
        depicts_member_name=context.depicts_member_name,
    )


def _with_source(
    context: ArtistContext,
    resolution_source: ResolutionSource,
) -> ArtistContext:
    """Return a copy of context with an updated resolution source."""
    if context.resolution_source == resolution_source:
        return context
    return ArtistContext(
        artist_mbid=context.artist_mbid,
        artist_type=context.artist_type,
        artist_country=context.artist_country,
        artist_disambiguation=context.artist_disambiguation,
        artist_tags=context.artist_tags,
        main_genres=context.main_genres,
        artist_members=context.artist_members,
        resolution_source=resolution_source,
        depicts_member_name=context.depicts_member_name,
    )


def _resolve_wikipedia_and_commons_fallbacks(
    artist_mbid: str,
    artist_name: str,
    *,
    wikidata_failure: ArtistImageRecord | None,
    context: ArtistContext,
) -> ArtistImageRecord:
    """Try Wikipedia and Commons when Wikidata is missing or MBID is unknown."""
    wikipedia_image, wikidata_id = _resolve_wikipedia_fallback(
        artist_mbid,
        artist_name,
        context=_with_source(context, "wikipedia"),
    )
    if wikipedia_image is not None:
        record = _ok_record_from_commons_info(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            commons_info=wikipedia_image,
            wikidata_id=wikidata_id
            or (wikidata_failure.wikidata_id if wikidata_failure else None),
            context=_with_source(context, "wikipedia"),
        )
        if record is not None:
            logger.info(
                "Resolved Wikipedia fallback for %s (%s): %s",
                artist_name,
                artist_mbid or "name-only",
                wikipedia_image.commons_file,
            )
            return record

    commons_image = find_commons_image_by_artist_name(
        artist_name,
        context=_with_source(context, "commons_search"),
    )
    if commons_image is not None:
        record = _ok_record_from_commons_info(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            commons_info=commons_image,
            wikidata_id=wikidata_failure.wikidata_id if wikidata_failure else None,
            context=_with_source(context, "commons_search"),
        )
        if record is not None:
            logger.info(
                "Resolved Commons search fallback for %s (%s): %s",
                artist_name,
                artist_mbid or "name-only",
                commons_image.commons_file,
            )
            return record

    if wikidata_failure is not None:
        return wikidata_failure

    return _not_found_record(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        reason="artist_not_found",
    )


def _resolve_member_fallback(
    artist_mbid: str,
    artist_name: str,
    *,
    context: ArtistContext,
    prior_failure: ArtistImageRecord,
) -> ArtistImageRecord:
    """Try member photos for groups when direct artist resolution failed."""
    if context.artist_type != "Group" or not context.artist_members:
        return prior_failure

    for member_name in context.artist_members:
        if not member_name_eligible_for_fallback(member_name):
            logger.info("Skipping member fallback for ambiguous name %s", member_name)
            continue
        member_context = ArtistContext(
            artist_mbid=context.artist_mbid,
            artist_type="Person",
            artist_country=context.artist_country,
            artist_disambiguation=context.artist_disambiguation,
            artist_tags=context.artist_tags,
            main_genres=context.main_genres,
            artist_members=context.artist_members,
            resolution_source="member_fallback",
            depicts_member_name=member_name,
        )
        commons_image = find_commons_image_by_artist_name(
            member_name,
            context=member_context,
        )
        if commons_image is None:
            continue
        record = _ok_record_from_commons_info(
            artist_mbid=artist_mbid,
            artist_name=artist_name,
            commons_info=commons_image,
            wikidata_id=None,
            context=member_context,
        )
        if record is not None:
            logger.info(
                "Resolved member fallback for %s via %s: %s",
                artist_name,
                member_name,
                commons_image.commons_file,
            )
            return record

    return prior_failure


def _resolve_wikipedia_fallback(
    artist_mbid: str,
    artist_name: str,
    *,
    context: ArtistContext,
) -> tuple[CommonsImageInfo | None, str | None]:
    """Try resolving an image via English Wikipedia article search."""
    if artist_mbid:
        disambiguation = context.artist_disambiguation or fetch_artist_disambiguation(
            artist_mbid,
        )
        search_names = build_wikipedia_search_names(
            artist_name,
            alias_names=fetch_artist_alias_names(artist_mbid),
            include_the_variants=disambiguation is None,
        )
        return find_commons_image_via_wikipedia(
            search_names,
            disambiguation=disambiguation,
            context=_with_source(context, "wikipedia"),
        )

    search_names = build_wikipedia_search_names(
        artist_name,
        alias_names=[],
        include_the_variants=True,
    )
    return find_commons_image_via_wikipedia(
        search_names,
        disambiguation=None,
        context=_with_source(context, "wikipedia"),
    )


def _resolve_via_wikidata(
    artist_mbid: str,
    artist_name: str,
    *,
    context: ArtistContext,
) -> ArtistImageRecord:
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

    record = _ok_record_from_commons_info(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        commons_info=commons_info,
        wikidata_id=wikidata_id,
        context=_with_source(context, "wikidata_p18"),
    )
    if record is not None:
        logger.info(
            "Resolved Wikidata image for %s (%s): %s",
            artist_name,
            artist_mbid,
            commons_info.commons_file,
        )
        return record

    logger.info(
        "Rejected Wikidata image %s for %s: low confidence",
        commons_info.commons_file,
        artist_name,
    )
    return _not_found_record(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        reason="low_confidence",
        wikidata_id=wikidata_id,
        commons_file=commons_info.commons_file,
    )


def _ok_record_from_commons_info(
    *,
    artist_mbid: str,
    artist_name: str,
    commons_info: CommonsImageInfo,
    wikidata_id: str | None,
    context: ArtistContext,
) -> ArtistImageRecord | None:
    """Build an ok record when confidence scoring accepts the Commons file."""
    confidence = score_parsed_commons_image(
        artist_name,
        commons_info,
        context=context,
        imageinfo=commons_info.imageinfo,
    )
    if not confidence.accepted:
        return None

    fields = commons_image_to_record_fields(commons_info)
    return ArtistImageRecord(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        status="ok",
        fetched_at=utc_now_iso(),
        wikidata_id=wikidata_id,
        commons_file=fields["commons_file"],
        image_url=fields["image_url"],
        thumbnail_url=fields["thumbnail_url"],
        license=fields["license"],
        license_url=fields["license_url"],
        author=fields["author"],
        source_url=fields["source_url"],
        attribution_text=fields["attribution_text"],
        confidence=confidence.score,
        resolution_source=context.resolution_source,
        validation_version=CURRENT_VALIDATION_VERSION,
        depicts_member_name=context.depicts_member_name,
    )


def _resolve_artist_identity(
    *,
    artist_mbid: str | None,
    artist_name: str | None,
    context: ArtistContext,
) -> tuple[str | None, str]:
    """Resolve artist MBID and display name."""
    requested_name = (artist_name or "").strip()

    if artist_mbid:
        mbid = artist_mbid.strip()
        if requested_name:
            info = fetch_artist_info_by_mbid(mbid)
            if info is not None and not musicbrainz_name_matches_requested(
                requested_name,
                info.name,
            ):
                logger.info(
                    "Rejected MusicBrainz MBID %s (%s) for requested name %s",
                    mbid,
                    info.name,
                    requested_name,
                )
                return None, requested_name
        return mbid, requested_name or mbid

    if requested_name:
        info = fetch_artist_info(requested_name)
        if info is None:
            return None, requested_name
        if not musicbrainz_name_matches_requested(requested_name, info.name):
            logger.info(
                "Rejected MusicBrainz match %s for requested name %s",
                info.name,
                requested_name,
            )
            return None, requested_name
        return info.mbid, info.name

    return None, ""


def revalidate_cached_record(
    record: ArtistImageRecord,
    *,
    context: ArtistContext | None = None,
) -> ArtistImageRecord:
    """Re-score one cached ok record with current validation rules."""
    if record.status != "ok" or not record.commons_file:
        return record

    resolved_context = context or ArtistContext(
        artist_mbid=record.artist_mbid or None,
        resolution_source=_parse_resolution_source(record.resolution_source),
        depicts_member_name=record.depicts_member_name,
    )
    title = f"File:{record.commons_file.replace(' ', '_')}"
    confidence = score_commons_image_candidate(
        record.artist_name,
        title,
        _imageinfo_from_record(record),
        context=resolved_context,
    )
    if confidence.accepted:
        if (
            record.confidence == confidence.score
            and record.validation_version == CURRENT_VALIDATION_VERSION
        ):
            return record
        return ArtistImageRecord(
            artist_mbid=record.artist_mbid,
            artist_name=record.artist_name,
            status="ok",
            fetched_at=utc_now_iso(),
            wikidata_id=record.wikidata_id,
            commons_file=record.commons_file,
            image_url=record.image_url,
            thumbnail_url=record.thumbnail_url,
            license=record.license,
            license_url=record.license_url,
            author=record.author,
            source_url=record.source_url,
            attribution_text=record.attribution_text,
            local_path=record.local_path,
            confidence=confidence.score,
            resolution_source=record.resolution_source,
            validation_version=CURRENT_VALIDATION_VERSION,
            depicts_member_name=record.depicts_member_name,
        )

    return _not_found_record(
        artist_mbid=record.artist_mbid,
        artist_name=record.artist_name,
        reason="revalidation_failed",
        wikidata_id=record.wikidata_id,
        commons_file=record.commons_file,
        reject_reasons=confidence.reasons,
    )


def _imageinfo_from_record(record: ArtistImageRecord) -> dict[str, object]:
    """Build minimal imageinfo for revalidation from a cached record."""
    extmetadata: dict[str, dict[str, str]] = {}
    if record.attribution_text:
        extmetadata["ImageDescription"] = {"value": record.attribution_text}
    if record.commons_file:
        extmetadata["ObjectName"] = {"value": record.commons_file}
    return {"extmetadata": extmetadata}


def _parse_resolution_source(value: str | None) -> ResolutionSource:
    """Parse a stored resolution source string."""
    if value == "wikidata_p18":
        return "wikidata_p18"
    if value == "wikipedia":
        return "wikipedia"
    if value == "commons_search":
        return "commons_search"
    if value == "member_fallback":
        return "member_fallback"
    return "commons_search"


def _not_found_record(
    *,
    artist_mbid: str,
    artist_name: str,
    reason: str,
    wikidata_id: str | None = None,
    commons_file: str | None = None,
    reject_reasons: list[str] | None = None,
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
        validation_version=CURRENT_VALIDATION_VERSION,
        reject_reasons=reject_reasons,
    )
