"""Cache-aware artist image lookups for the Plattenradar API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import getenv
from pathlib import Path

from music_review.application.artist_image_download import (
    artist_image_download_enabled,
    download_thumbnail,
    local_image_file_path,
    local_image_relative_path,
)
from music_review.application.artist_image_lookup import (
    artist_image_lookup_key,
)
from music_review.application.artist_image_models import ArtistImageRecord
from music_review.application.artist_image_resolver import (
    resolve_artist_image,
    revalidate_cached_record,
)
from music_review.application.artist_image_store import (
    load_artist_image_index,
    upsert_artist_image,
)
from music_review.data_access.paths import artist_images_dir, artist_images_path
from music_review.pipeline.enrichment.commons_artist_match import (
    cached_commons_image_matches_artist,
    record_matches_artist_name,
)
from music_review.pipeline.enrichment.commons_image_confidence import ArtistContext

logger = logging.getLogger(__name__)

DEFAULT_NEGATIVE_CACHE_TTL_DAYS = 30


def resolve_on_demand_enabled() -> bool:
    """Return whether API lookups may trigger external image resolution."""
    return getenv("ARTIST_IMAGE_RESOLVE_ON_DEMAND", "false").lower() == "true"


def negative_cache_ttl_days() -> int:
    """Return the TTL for negative artist image cache entries."""
    raw = getenv("ARTIST_IMAGE_CACHE_TTL_DAYS", str(DEFAULT_NEGATIVE_CACHE_TTL_DAYS))
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_NEGATIVE_CACHE_TTL_DAYS
    return max(1, parsed)


def is_negative_cache_fresh(
    record: ArtistImageRecord,
    *,
    ttl_days: int,
    now: datetime | None = None,
) -> bool:
    """Return whether a not_found record should block another external lookup."""
    if record.status != "not_found":
        return False
    fetched_at = _parse_fetched_at(record.fetched_at)
    if fetched_at is None:
        return False
    current = now or datetime.now(UTC)
    return current - fetched_at < timedelta(days=ttl_days)


@dataclass(slots=True)
class ArtistImageService:
    """Resolve artist images with JSONL caching and negative-cache TTL."""

    cache_path: Path
    images_dir: Path
    negative_ttl_days: int = DEFAULT_NEGATIVE_CACHE_TTL_DAYS
    download_enabled: bool = False
    resolve_on_demand: bool = True

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
        force: bool = False,
        context: ArtistContext | None = None,
    ) -> ArtistImageRecord:
        """Return a cached or freshly resolved artist image record."""
        if not self.resolve_on_demand and not force:
            return self.lookup_cached_only(artist_mbid, artist_name=artist_name)
        mbid = artist_mbid.strip()
        if mbid:
            return self._lookup_by_mbid(
                mbid,
                artist_name=artist_name,
                force=force,
                context=context,
            )

        name = (artist_name or "").strip()
        if not name:
            return _empty_not_found_record()

        return self._lookup_by_name(name, force=force, context=context)

    def lookup_cached_only(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Return a cached record without triggering external resolution."""
        lookup_key = artist_image_lookup_key(artist_mbid, artist_name=artist_name)
        if not lookup_key:
            return _empty_not_found_record()

        cached = self.cached_record(lookup_key)
        if cached is None:
            return _synthetic_not_found(
                lookup_key,
                artist_name or lookup_key,
                reason="cache_miss",
            )
        if cached.status == "ok":
            if self._cached_image_matches_artist(cached, artist_name=artist_name):
                return self._restore_resolved_record(cached)
            return _synthetic_not_found(
                lookup_key,
                artist_name or cached.artist_name,
                reason="cache_name_mismatch",
            )
        if self.is_negative_cache_fresh(cached):
            return cached
        return _synthetic_not_found(
            lookup_key,
            artist_name or cached.artist_name,
            reason="cache_miss",
        )

    def _lookup_by_mbid(
        self,
        mbid: str,
        *,
        artist_name: str | None = None,
        force: bool = False,
        context: ArtistContext | None = None,
    ) -> ArtistImageRecord:
        """Resolve one artist image when a MusicBrainz MBID is known."""
        if not force:
            cached = self.cached_record(mbid)
            if cached is not None:
                if cached.status == "ok":
                    if self._cached_image_matches_artist(
                        cached,
                        artist_name=artist_name,
                    ):
                        logger.debug("Artist image cache hit for %s", mbid)
                        return self._ensure_local_copy(cached)
                    logger.warning(
                        "Artist image cache mismatch for %s; re-resolving",
                        mbid,
                    )
                elif self.is_negative_cache_fresh(cached):
                    logger.debug("Artist image negative cache hit for %s", mbid)
                    return cached

        record = resolve_artist_image(
            artist_mbid=mbid,
            artist_name=artist_name,
            context=context,
        )
        record = self._validate_resolved_record(record, artist_name=artist_name)
        record = self._ensure_local_copy(record)
        upsert_artist_image(self.cache_path, record)
        return record

    def _lookup_by_name(
        self,
        artist_name: str,
        *,
        force: bool = False,
        context: ArtistContext | None = None,
    ) -> ArtistImageRecord:
        """Resolve one artist image from a display name when no MBID is known."""
        lookup_key = artist_image_lookup_key(None, artist_name=artist_name)
        if not force:
            cached = self.cached_record(lookup_key)
            if cached is not None:
                if cached.status == "ok":
                    if self._cached_image_matches_artist(
                        cached,
                        artist_name=artist_name,
                    ):
                        logger.debug("Artist image name-cache hit for %s", artist_name)
                        return self._restore_resolved_record(cached)
                    logger.warning(
                        "Artist image name-cache mismatch for %s; re-resolving",
                        artist_name,
                    )
                elif self.is_negative_cache_fresh(cached):
                    logger.debug(
                        "Artist image negative name-cache hit for %s",
                        artist_name,
                    )
                    return cached

        record = resolve_artist_image(
            artist_mbid=None,
            artist_name=artist_name,
            context=context,
        )
        record = self._validate_resolved_record(record, artist_name=artist_name)
        record = self._ensure_local_copy(record)
        self._persist_name_lookup(record, lookup_key)
        return record

    def _persist_name_lookup(
        self,
        record: ArtistImageRecord,
        lookup_key: str,
    ) -> None:
        """Store a name-based lookup and optional resolved MBID cache entry."""
        if record.artist_mbid:
            upsert_artist_image(self.cache_path, record)
            if record.status == "ok":
                upsert_artist_image(
                    self.cache_path,
                    _artist_image_alias(record, lookup_key),
                )
            return

        upsert_artist_image(self.cache_path, _artist_image_alias(record, lookup_key))

    def _restore_resolved_record(self, cached: ArtistImageRecord) -> ArtistImageRecord:
        """Return a usable record for one cache hit."""
        return cached

    def _cached_image_matches_artist(
        self,
        record: ArtistImageRecord,
        *,
        artist_name: str | None = None,
    ) -> bool:
        """Return whether a cached ok record matches the expected artist name."""
        if record.status != "ok":
            return True
        expected = (artist_name or record.artist_name).strip()
        return cached_commons_image_matches_artist(
            expected,
            commons_file=record.commons_file,
            attribution_text=record.attribution_text,
            source_url=record.source_url,
        )

    def _validate_resolved_record(
        self,
        record: ArtistImageRecord,
        *,
        artist_name: str | None,
    ) -> ArtistImageRecord:
        """Reject resolved images that do not match the requested artist name."""
        expected = (artist_name or "").strip()
        if not expected or record.status != "ok":
            return record
        if record_matches_artist_name(
            expected,
            commons_file=record.commons_file,
            attribution_text=record.attribution_text,
            source_url=record.source_url,
        ):
            return record

        logger.info(
            "Rejected artist image for %s: Commons context does not match %s",
            record.commons_file,
            expected,
        )
        from music_review.application.artist_image_models import utc_now_iso

        return ArtistImageRecord(
            artist_mbid=record.artist_mbid,
            artist_name=expected,
            status="not_found",
            fetched_at=utc_now_iso(),
            wikidata_id=record.wikidata_id,
            commons_file=record.commons_file,
            reason="artist_name_mismatch",
        )

    def lookup_batch(
        self,
        artists: list[tuple[str, str | None]],
        *,
        cached_only: bool = False,
    ) -> dict[str, ArtistImageRecord]:
        """Resolve multiple artist images, reusing cache entries when possible."""
        results: dict[str, ArtistImageRecord] = {}
        for artist_mbid, artist_name in artists:
            lookup_key = artist_image_lookup_key(artist_mbid, artist_name=artist_name)
            if not lookup_key or lookup_key in results:
                continue
            if cached_only or not self.resolve_on_demand:
                results[lookup_key] = self.lookup_cached_only(
                    artist_mbid,
                    artist_name=artist_name,
                )
            else:
                results[lookup_key] = self.lookup(
                    artist_mbid,
                    artist_name=artist_name,
                )
        return results

    def revalidate_record(
        self,
        record: ArtistImageRecord,
        *,
        context: ArtistContext | None = None,
    ) -> ArtistImageRecord:
        """Re-score one cached record and persist when it changes."""
        updated = revalidate_cached_record(record, context=context)
        if (
            updated.status != record.status
            or updated.validation_version != record.validation_version
            or updated.confidence != record.confidence
        ):
            upsert_artist_image(self.cache_path, updated)
        return updated

    def cached_record(self, artist_mbid: str) -> ArtistImageRecord | None:
        """Return one cached record when present."""
        if not self.cache_path.is_file():
            return None
        return load_artist_image_index(self.cache_path).get(artist_mbid.strip())

    def is_negative_cache_fresh(self, record: ArtistImageRecord) -> bool:
        """Return whether a negative cache entry is still valid."""
        return is_negative_cache_fresh(record, ttl_days=self.negative_ttl_days)

    def public_thumbnail_url(self, record: ArtistImageRecord) -> str | None:
        """Return the API URL for a locally stored thumbnail, if available."""
        if record.status != "ok" or not self.local_file_exists(record):
            return None
        return f"/v1/artists/{record.artist_mbid}/image/file"

    def local_file_exists(self, record: ArtistImageRecord) -> bool:
        """Return whether a local JPG exists for one cached record."""
        local_path = self.resolve_local_file_path(record)
        return local_path is not None and local_path.is_file()

    def resolve_local_file_path(self, record: ArtistImageRecord) -> Path | None:
        """Return the on-disk JPG path for one record when known."""
        if record.local_path:
            candidate = self.images_dir.parent / record.local_path
            if candidate.is_file():
                return candidate
        return local_image_file_path(self.images_dir, record.artist_mbid)

    def _ensure_local_copy(self, record: ArtistImageRecord) -> ArtistImageRecord:
        """Download and persist a local thumbnail when enabled and possible."""
        if record.status != "ok" or not record.thumbnail_url:
            return record
        if not self.download_enabled:
            return record

        dest_path = local_image_file_path(self.images_dir, record.artist_mbid)
        if dest_path.is_file():
            relative_path = local_image_relative_path(record.artist_mbid)
            return _with_local_path(record, relative_path)

        if not download_thumbnail(record.thumbnail_url, dest_path):
            return record

        return _with_local_path(record, local_image_relative_path(record.artist_mbid))


def default_artist_image_service() -> ArtistImageService:
    """Build the default on-disk artist image service."""
    return ArtistImageService(
        cache_path=artist_images_path(),
        images_dir=artist_images_dir(),
        negative_ttl_days=negative_cache_ttl_days(),
        download_enabled=artist_image_download_enabled(),
        resolve_on_demand=resolve_on_demand_enabled(),
    )


def _artist_image_alias(
    record: ArtistImageRecord,
    lookup_key: str,
) -> ArtistImageRecord:
    """Build a name-keyed cache alias for one resolved artist image."""
    return ArtistImageRecord(
        artist_mbid=lookup_key,
        artist_name=record.artist_name,
        status=record.status,
        fetched_at=record.fetched_at,
        wikidata_id=record.wikidata_id,
        commons_file=record.commons_file,
        image_url=record.image_url,
        thumbnail_url=record.thumbnail_url,
        license=record.license,
        license_url=record.license_url,
        author=record.author,
        source_url=record.source_url,
        attribution_text=record.attribution_text,
        reason=record.reason,
        local_path=None,
        confidence=record.confidence,
        resolution_source=record.resolution_source,
        validation_version=record.validation_version,
        depicts_member_name=record.depicts_member_name,
        reject_reasons=record.reject_reasons,
    )


def _with_local_path(record: ArtistImageRecord, local_path: str) -> ArtistImageRecord:
    """Return a copy of a record with an updated local_path."""
    if record.local_path == local_path:
        return record
    return ArtistImageRecord(
        artist_mbid=record.artist_mbid,
        artist_name=record.artist_name,
        status=record.status,
        fetched_at=record.fetched_at,
        wikidata_id=record.wikidata_id,
        commons_file=record.commons_file,
        image_url=record.image_url,
        thumbnail_url=record.thumbnail_url,
        license=record.license,
        license_url=record.license_url,
        author=record.author,
        source_url=record.source_url,
        attribution_text=record.attribution_text,
        reason=record.reason,
        local_path=local_path,
        confidence=record.confidence,
        resolution_source=record.resolution_source,
        validation_version=record.validation_version,
        depicts_member_name=record.depicts_member_name,
        reject_reasons=record.reject_reasons,
    )


def _synthetic_not_found(
    lookup_key: str,
    artist_name: str,
    *,
    reason: str,
) -> ArtistImageRecord:
    """Build a non-persisted not_found record for cache-only API misses."""
    from music_review.application.artist_image_models import utc_now_iso

    return ArtistImageRecord(
        artist_mbid=lookup_key,
        artist_name=artist_name,
        status="not_found",
        fetched_at=utc_now_iso(),
        reason=reason,
    )


def _empty_not_found_record() -> ArtistImageRecord:
    """Build a synthetic not_found record for invalid MBIDs."""
    from music_review.application.artist_image_models import utc_now_iso

    return ArtistImageRecord(
        artist_mbid="",
        artist_name="",
        status="not_found",
        fetched_at=utc_now_iso(),
        reason="invalid_mbid",
    )


def _parse_fetched_at(value: str) -> datetime | None:
    """Parse an ISO timestamp from cache records."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
