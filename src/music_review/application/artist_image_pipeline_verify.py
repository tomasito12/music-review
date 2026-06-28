"""Helpers to verify that cached artist images are API-ready."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from music_review.application.artist_image_lookup import artist_image_lookup_key
from music_review.application.artist_image_service import ArtistImageService
from music_review.application.artist_image_store import load_artist_image_index
from music_review.data_access.paths import artist_images_dir, artist_images_path

ArtistImagePipelineStatus = Literal[
    "ready",
    "missing_jsonl",
    "jsonl_not_ok",
    "missing_jpg",
    "api_no_image",
    "api_file_missing",
]


@dataclass(frozen=True, slots=True)
class ArtistImagePipelineCheck:
    """Result of one artist image readiness check."""

    lookup_key: str
    artist_name: str
    status: ArtistImagePipelineStatus
    detail: str


@dataclass(frozen=True, slots=True)
class ArtistImagePipelineReport:
    """Summary of multiple artist image readiness checks."""

    checks: tuple[ArtistImagePipelineCheck, ...]

    @property
    def ready_count(self) -> int:
        """Return how many artists are fully ready for the UI."""
        return sum(1 for check in self.checks if check.status == "ready")


def check_local_artist_image_cache(
    lookup_key: str,
    *,
    artist_name: str,
    cache_path: Path | None = None,
    images_dir: Path | None = None,
) -> ArtistImagePipelineCheck:
    """Verify JSONL and JPG cache entries for one lookup key."""
    resolved_cache_path = cache_path or artist_images_path()
    resolved_images_dir = images_dir or artist_images_dir()
    service = ArtistImageService(
        cache_path=resolved_cache_path,
        images_dir=resolved_images_dir,
        resolve_on_demand=False,
    )
    record = service.cached_record(lookup_key)
    if record is None:
        return ArtistImagePipelineCheck(
            lookup_key=lookup_key,
            artist_name=artist_name,
            status="missing_jsonl",
            detail="No cache entry in artist_images.jsonl",
        )
    if record.status != "ok":
        return ArtistImagePipelineCheck(
            lookup_key=lookup_key,
            artist_name=artist_name,
            status="jsonl_not_ok",
            detail=f"Cache status is {record.status!r}",
        )
    if not service.local_file_exists(record):
        return ArtistImagePipelineCheck(
            lookup_key=lookup_key,
            artist_name=artist_name,
            status="missing_jpg",
            detail="JSONL ok but local JPG is missing under data/artist_images/",
        )
    return ArtistImagePipelineCheck(
        lookup_key=lookup_key,
        artist_name=artist_name,
        status="ready",
        detail="JSONL ok and local JPG exists",
    )


def check_artist_image_api_readiness(
    lookup_key: str,
    *,
    artist_name: str,
    artist_mbid: str = "",
    service: ArtistImageService | None = None,
) -> ArtistImagePipelineCheck:
    """Verify cache, batch API mapping, and local file endpoint readiness."""
    local_check = check_local_artist_image_cache(
        lookup_key,
        artist_name=artist_name,
        cache_path=service.cache_path if service is not None else None,
        images_dir=service.images_dir if service is not None else None,
    )
    if local_check.status != "ready":
        return local_check

    resolved_service = service or ArtistImageService(
        cache_path=artist_images_path(),
        images_dir=artist_images_dir(),
        resolve_on_demand=False,
    )
    record = resolved_service.lookup_cached_only(
        artist_mbid or lookup_key,
        artist_name=artist_name,
    )
    thumbnail_url = resolved_service.public_thumbnail_url(record)
    if record.status != "ok" or thumbnail_url is None:
        return ArtistImagePipelineCheck(
            lookup_key=lookup_key,
            artist_name=artist_name,
            status="api_no_image",
            detail="Local cache exists but API would return image=null",
        )

    local_path = resolved_service.resolve_local_file_path(record)
    if local_path is None or not local_path.is_file():
        return ArtistImagePipelineCheck(
            lookup_key=lookup_key,
            artist_name=artist_name,
            status="api_file_missing",
            detail="API thumbnail URL exists but image/file path is missing",
        )

    return ArtistImagePipelineCheck(
        lookup_key=lookup_key,
        artist_name=artist_name,
        status="ready",
        detail=f"API ready via {thumbnail_url}",
    )


def sample_lookup_keys_from_cache(
    *,
    cache_path: Path | None = None,
    limit: int = 5,
) -> list[tuple[str, str]]:
    """Return up to ``limit`` ok lookup keys with artist names from the cache."""
    resolved_cache_path = cache_path or artist_images_path()
    if not resolved_cache_path.is_file():
        return []

    records = load_artist_image_index(resolved_cache_path)
    samples: list[tuple[str, str]] = []
    for lookup_key, record in records.items():
        if record.status != "ok":
            continue
        samples.append((lookup_key, record.artist_name))
        if len(samples) >= limit:
            break
    return samples


def artist_targets_from_recommendation_items(
    items: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[tuple[str, str, str]]:
    """Build artist lookup tuples from API recommendation items."""
    targets: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for item in items:
        artist_name = str(item.get("artist", "")).strip()
        artist_mbid = item.get("artist_mbid")
        mbid = artist_mbid.strip() if isinstance(artist_mbid, str) else ""
        lookup_key = artist_image_lookup_key(mbid or None, artist_name=artist_name)
        if not lookup_key or lookup_key in seen:
            continue
        seen.add(lookup_key)
        targets.append((lookup_key, artist_name, mbid))
        if len(targets) >= limit:
            break
    return targets


def verify_artist_image_pipeline(
    targets: list[tuple[str, str, str]],
    *,
    service: ArtistImageService | None = None,
) -> ArtistImagePipelineReport:
    """Run readiness checks for multiple artist lookup targets."""
    checks = [
        check_artist_image_api_readiness(
            lookup_key,
            artist_name=artist_name,
            artist_mbid=artist_mbid,
            service=service,
        )
        for lookup_key, artist_name, artist_mbid in targets
    ]
    return ArtistImagePipelineReport(checks=tuple(checks))
