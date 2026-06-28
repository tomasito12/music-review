"""Batch and pipeline helpers for artist image caching."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from music_review.application.artist_image_lookup import artist_image_lookup_key
from music_review.application.artist_image_models import ArtistImageRecord
from music_review.application.artist_image_service import ArtistImageService
from music_review.application.artist_image_store import load_artist_image_index
from music_review.io.jsonl import iter_jsonl_objects
from music_review.pipeline.enrichment.commons_image_confidence import ArtistContext

logger = logging.getLogger(__name__)

DEFAULT_FETCH_LIMIT = 25
ArtistImageQueue = Literal["mbid", "name", "all"]


@dataclass(slots=True, frozen=True)
class ArtistImageTarget:
    """One artist row scheduled for offline image resolution."""

    lookup_key: str
    artist_name: str
    artist_mbid: str | None
    artist_type: str | None
    artist_country: str | None
    artist_disambiguation: str | None
    artist_members: tuple[str, ...]
    main_genres: tuple[str, ...]
    review_count: int

    def to_context(self) -> ArtistContext:
        """Build resolver context from aggregated metadata hints."""
        return ArtistContext(
            artist_mbid=self.artist_mbid,
            artist_type=self.artist_type,
            artist_country=self.artist_country,
            artist_disambiguation=self.artist_disambiguation,
            main_genres=self.main_genres,
            artist_members=self.artist_members,
        )


@dataclass(slots=True)
class ArtistImageBatchReport:
    """Summary counters for one batch run."""

    attempted: int = 0
    resolved_ok: int = 0
    not_found: int = 0
    skipped_cached: int = 0
    rejected_low_confidence: int = 0
    revalidated_downgraded: int = 0

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-serializable summary."""
        return asdict(self)


def unique_artists_from_metadata(
    metadata_path: Path,
) -> list[tuple[str, str]]:
    """Return unique (artist_mbid, artist_name) pairs from metadata JSONL."""
    targets = artist_targets_from_metadata(metadata_path)
    return [
        (target.artist_mbid, target.artist_name)
        for target in targets
        if target.artist_mbid
    ]


def artist_targets_from_metadata(
    metadata_path: Path,
    *,
    artist_genres_path: Path | None = None,
    review_ids: frozenset[int] | None = None,
) -> list[ArtistImageTarget]:
    """Aggregate unique artist targets with metadata hints from JSONL."""
    if not metadata_path.is_file():
        return []

    genre_map = _load_artist_genre_map(artist_genres_path)
    grouped: dict[str, dict[str, Any]] = {}

    for obj in iter_jsonl_objects(metadata_path, log_errors=False):
        if review_ids is not None:
            review_id = obj.get("review_id")
            if not isinstance(review_id, int) or review_id not in review_ids:
                continue

        artist_name = obj.get("artist")
        name = str(artist_name).strip() if artist_name else ""
        if not name:
            continue

        artist_mbid = obj.get("artist_mbid")
        mbid = artist_mbid.strip() if isinstance(artist_mbid, str) else ""
        group_key = mbid or _normalized_name_key(name)
        bucket = grouped.setdefault(
            group_key,
            {
                "artist_name": name,
                "artist_mbid": mbid or None,
                "artist_type": None,
                "artist_country": None,
                "artist_disambiguation": None,
                "artist_members": set[str](),
                "main_genres": set[str](),
                "review_count": 0,
            },
        )
        bucket["review_count"] = int(bucket["review_count"]) + 1
        if mbid and not bucket["artist_mbid"]:
            bucket["artist_mbid"] = mbid
        if not bucket["artist_name"]:
            bucket["artist_name"] = name

        for field in ("artist_type", "artist_country", "artist_disambiguation"):
            value = obj.get(field)
            if isinstance(value, str) and value.strip() and not bucket[field]:
                bucket[field] = value.strip()

        members = obj.get("artist_members")
        if isinstance(members, list):
            for member in members:
                if isinstance(member, str) and member.strip():
                    bucket["artist_members"].add(member.strip())

        genres = genre_map.get(_genre_lookup_key(mbid, name), ())
        bucket["main_genres"].update(genres)

    targets: list[ArtistImageTarget] = []
    for bucket in grouped.values():
        artist_name = str(bucket["artist_name"])
        artist_mbid = bucket["artist_mbid"]
        lookup_key = artist_image_lookup_key(artist_mbid, artist_name=artist_name)
        if not lookup_key:
            continue
        targets.append(
            ArtistImageTarget(
                lookup_key=lookup_key,
                artist_name=artist_name,
                artist_mbid=artist_mbid,
                artist_type=bucket["artist_type"],
                artist_country=bucket["artist_country"],
                artist_disambiguation=bucket["artist_disambiguation"],
                artist_members=tuple(sorted(bucket["artist_members"])),
                main_genres=tuple(sorted(bucket["main_genres"])),
                review_count=int(bucket["review_count"]),
            ),
        )

    targets.sort(key=lambda item: (-item.review_count, item.artist_name.casefold()))
    return targets


def split_targets_by_queue(
    targets: Sequence[ArtistImageTarget],
    *,
    queue: ArtistImageQueue = "all",
) -> list[ArtistImageTarget]:
    """Filter targets into MBID-first or name-only queues."""
    if queue == "mbid":
        return [target for target in targets if target.artist_mbid]
    if queue == "name":
        return [target for target in targets if not target.artist_mbid]
    return list(targets)


def batch_selection_slice(
    targets: Sequence[ArtistImageTarget],
    *,
    offset: int,
    limit: int,
    process_all: bool = False,
) -> list[ArtistImageTarget]:
    """Return the artist slice selected for one batch run."""
    start = max(0, offset)
    if process_all:
        return list(targets[start:])
    return list(targets[start : start + max(1, limit)])


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


def run_artist_image_batch(
    service: ArtistImageService,
    targets: Sequence[ArtistImageTarget],
    *,
    limit: int,
    offset: int = 0,
    missing_only: bool = True,
    force: bool = False,
    revalidate: bool = False,
    process_all: bool = False,
) -> ArtistImageBatchReport:
    """Resolve or revalidate artist images for one target slice."""
    report = ArtistImageBatchReport()
    selected = batch_selection_slice(
        targets,
        offset=offset,
        limit=limit,
        process_all=process_all,
    )

    for target in selected:
        cached = service.cached_record(target.lookup_key)
        if revalidate:
            if cached is None or cached.status != "ok":
                continue
            report.attempted += 1
            updated = service.revalidate_record(cached, context=target.to_context())
            if updated.status != "ok":
                report.revalidated_downgraded += 1
                report.not_found += 1
            continue

        if missing_only and not force and cached is not None:
            if cached.status == "ok":
                if not _cached_record_needs_local_download(service, cached):
                    report.skipped_cached += 1
                    continue
            elif service.is_negative_cache_fresh(cached):
                report.skipped_cached += 1
                continue

        report.attempted += 1
        try:
            record = service.lookup(
                target.artist_mbid or "",
                artist_name=target.artist_name,
                force=force,
                context=target.to_context(),
            )
        except Exception:
            logger.exception(
                "Artist image lookup failed for lookup_key=%s artist=%s",
                target.lookup_key,
                target.artist_name,
            )
            report.not_found += 1
            continue
        if record.status == "ok":
            report.resolved_ok += 1
        else:
            report.not_found += 1
            if record.reason in {"low_confidence", "revalidation_failed"}:
                report.rejected_low_confidence += 1

    logger.info(
        "Artist image batch complete: %s",
        report.to_dict(),
    )
    return report


def _cached_record_needs_local_download(
    service: ArtistImageService,
    cached: ArtistImageRecord,
) -> bool:
    """Return whether a cached ok record still needs a local JPG download."""
    if cached.status != "ok" or not cached.thumbnail_url:
        return False
    if not service.download_enabled:
        return False
    return not service.local_file_exists(cached)


def write_batch_report(report: ArtistImageBatchReport, report_path: Path) -> None:
    """Persist one batch summary as JSON."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def _load_artist_genre_map(
    artist_genres_path: Path | None,
) -> dict[str, tuple[str, ...]]:
    """Load main genres keyed by MBID or normalized artist name."""
    if artist_genres_path is None or not artist_genres_path.is_file():
        return {}

    mapping: dict[str, tuple[str, ...]] = {}
    raw = json.loads(artist_genres_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return mapping

    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        genres = value.get("main_genres")
        if not isinstance(genres, list):
            continue
        genre_tuple = tuple(
            str(genre).strip() for genre in genres if str(genre).strip()
        )
        if not genre_tuple:
            continue
        mapping[str(key)] = genre_tuple
        artist_name = value.get("artist_name")
        if isinstance(artist_name, str) and artist_name.strip():
            mapping[_normalized_name_key(artist_name)] = genre_tuple
        artist_mbid = value.get("artist_mbid")
        if isinstance(artist_mbid, str) and artist_mbid.strip():
            mapping[f"mbid:{artist_mbid.strip()}"] = genre_tuple
    return mapping


def _genre_lookup_key(artist_mbid: str, artist_name: str) -> str:
    """Build a lookup key for artist genre hints."""
    if artist_mbid:
        return f"mbid:{artist_mbid}"
    return _normalized_name_key(artist_name)


def _normalized_name_key(artist_name: str) -> str:
    """Normalize one artist display name for grouping."""
    return f"name:{artist_name.strip().casefold()}"


def load_cached_records(path: Path) -> dict[str, ArtistImageRecord]:
    """Load all cached artist image records from JSONL."""
    if not path.is_file():
        return {}
    return load_artist_image_index(path)
