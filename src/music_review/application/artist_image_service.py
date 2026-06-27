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
from music_review.application.artist_image_models import ArtistImageRecord
from music_review.application.artist_image_resolver import resolve_artist_image
from music_review.application.artist_image_store import (
    load_artist_image_index,
    upsert_artist_image,
)
from music_review.data_access.paths import artist_images_dir, artist_images_path

logger = logging.getLogger(__name__)

DEFAULT_NEGATIVE_CACHE_TTL_DAYS = 30


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

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Return a cached or freshly resolved artist image record."""
        mbid = artist_mbid.strip()
        if not mbid:
            return _empty_not_found_record()

        cached = self.cached_record(mbid)
        if cached is not None:
            if cached.status == "ok":
                logger.debug("Artist image cache hit for %s", mbid)
                return self._ensure_local_copy(cached)
            if self.is_negative_cache_fresh(cached):
                logger.debug("Artist image negative cache hit for %s", mbid)
                return cached

        record = resolve_artist_image(artist_mbid=mbid, artist_name=artist_name)
        record = self._ensure_local_copy(record)
        upsert_artist_image(self.cache_path, record)
        return record

    def lookup_batch(
        self,
        artists: list[tuple[str, str | None]],
    ) -> dict[str, ArtistImageRecord]:
        """Resolve multiple artist images, reusing cache entries when possible."""
        results: dict[str, ArtistImageRecord] = {}
        for artist_mbid, artist_name in artists:
            mbid = artist_mbid.strip()
            if not mbid or mbid in results:
                continue
            results[mbid] = self.lookup(mbid, artist_name=artist_name)
        return results

    def cached_record(self, artist_mbid: str) -> ArtistImageRecord | None:
        """Return one cached record when present."""
        if not self.cache_path.is_file():
            return None
        return load_artist_image_index(self.cache_path).get(artist_mbid.strip())

    def is_negative_cache_fresh(self, record: ArtistImageRecord) -> bool:
        """Return whether a negative cache entry is still valid."""
        return is_negative_cache_fresh(record, ttl_days=self.negative_ttl_days)

    def public_thumbnail_url(self, record: ArtistImageRecord) -> str | None:
        """Return the API or remote URL clients should use for the thumbnail."""
        if record.status != "ok":
            return None
        if self.local_file_exists(record):
            return f"/v1/artists/{record.artist_mbid}/image/file"
        return record.thumbnail_url

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
