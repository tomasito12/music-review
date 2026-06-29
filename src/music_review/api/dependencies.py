"""Data providers and dependency hooks for the HTTP API."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from fastapi import Header

from music_review.application.artist_image_service import (
    ArtistImageService,
    default_artist_image_service,
)
from music_review.dashboard.user_db import get_connection
from music_review.data_access.affinities import affinities_by_review_id, affinities_list
from music_review.data_access.communities import (
    load_artist_communities,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
)
from music_review.data_access.metadata import load_metadata_map
from music_review.data_access.paths import (
    album_community_affinities_path,
    communities_res_10_path,
    community_broad_categories_res_10_path,
    community_genre_labels_res_10_path,
    community_memberships_path,
    metadata_path,
    reviews_path,
)
from music_review.data_access.reviews import (
    YEAR_SLIDER_FALLBACK_FLOOR,
    load_reviews,
    max_release_year_in_jsonl,
    min_release_year_in_jsonl,
    unique_plattenlabels_from_reviews_jsonl,
)
from music_review.domain.models import Review


class CorpusProvider(Protocol):
    """Loader interface used by API endpoints."""

    def reviews(self) -> Sequence[Review]:
        """Return the full review corpus."""

    def newest_reviews(self, count: int) -> Sequence[Review]:
        """Return the newest reviews by corpus id."""

    def metadata(self) -> Mapping[int, Mapping[str, Any]]:
        """Return metadata keyed by review id."""

    def affinities(self) -> Sequence[Mapping[str, Any]]:
        """Return album-community affinities as raw records."""

    def affinities_by_review_id(self) -> Mapping[int, Mapping[str, Any]]:
        """Return album-community affinities keyed by review id."""

    def memberships(self) -> dict[str, dict[str, str]]:
        """Return artist-community memberships."""

    def communities(self) -> Sequence[Mapping[str, Any]]:
        """Return community metadata."""

    def broad_categories(self) -> tuple[list[str], dict[str, list[str]]]:
        """Return broad category labels and community assignments."""

    def genre_labels(self) -> Mapping[str, str]:
        """Return readable community labels."""

    def plattenlabels(self) -> Sequence[str]:
        """Return known record labels from the review corpus."""

    def year_floor(self) -> int:
        """Return the lowest release year known to the corpus."""

    def year_cap(self) -> int:
        """Return the highest release year known to the corpus."""

    def artist_mbid_for_review(self, review_id: int) -> str | None:
        """Return the MusicBrainz artist ID for one review, if known."""


@dataclass(frozen=True, slots=True)
class FileCorpusProvider:
    """Corpus provider backed by local project data files."""

    def reviews(self) -> Sequence[Review]:
        """Return all local reviews."""
        return load_reviews()

    def newest_reviews(self, count: int) -> Sequence[Review]:
        """Return the newest local reviews by descending review id."""
        reviews = list(load_reviews())
        reviews.sort(key=lambda review: int(review.id), reverse=True)
        return reviews[: max(1, count)]

    def metadata(self) -> Mapping[int, Mapping[str, Any]]:
        """Return local metadata keyed by review id."""
        return load_metadata_map()

    def affinities(self) -> Sequence[Mapping[str, Any]]:
        """Return local affinity records."""
        return affinities_list()

    def affinities_by_review_id(self) -> Mapping[int, Mapping[str, Any]]:
        """Return local affinity records keyed by review id."""
        return affinities_by_review_id()

    def memberships(self) -> dict[str, dict[str, str]]:
        """Return local artist-community memberships."""
        return load_artist_communities()

    def communities(self) -> Sequence[Mapping[str, Any]]:
        """Return local resolution-10 community metadata."""
        return load_communities_res_10()

    def broad_categories(self) -> tuple[list[str], dict[str, list[str]]]:
        """Return local broad categories and community assignments."""
        return load_broad_categories_res_10()

    def genre_labels(self) -> Mapping[str, str]:
        """Return local generated community labels."""
        return load_genre_labels_res_10()

    def plattenlabels(self) -> Sequence[str]:
        """Return local sorted record labels."""
        return unique_plattenlabels_from_reviews_jsonl(reviews_path())

    def year_floor(self) -> int:
        """Return the lowest release year known to local reviews."""
        return min_release_year_in_jsonl(reviews_path()) or YEAR_SLIDER_FALLBACK_FLOOR

    def year_cap(self) -> int:
        """Return the highest release year known to local reviews."""
        return max_release_year_in_jsonl(reviews_path()) or datetime.now().year

    def artist_mbid_for_review(self, review_id: int) -> str | None:
        """Return the MusicBrainz artist ID for one local review, if known."""
        return _artist_mbid_from_metadata(self.metadata(), review_id)


def _corpus_source_mtimes() -> tuple[float, ...]:
    """Return mtimes for corpus files used to detect local data updates."""
    paths = (
        reviews_path(),
        album_community_affinities_path(),
        metadata_path(),
        community_memberships_path(),
        communities_res_10_path(),
        community_genre_labels_res_10_path(),
        community_broad_categories_res_10_path(),
    )
    return tuple(path.stat().st_mtime if path.is_file() else 0.0 for path in paths)


@dataclass
class CachedCorpusProvider:
    """In-memory corpus cache with invalidation when source files change."""

    source: FileCorpusProvider
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _source_mtimes: tuple[float, ...] | None = None
    _reviews: list[Review] | None = None
    _metadata: Mapping[int, Mapping[str, Any]] | None = None
    _affinities: list[Mapping[str, Any]] | None = None
    _affinities_by_review_id: Mapping[int, Mapping[str, Any]] | None = None
    _memberships: dict[str, dict[str, str]] | None = None
    _communities: list[Mapping[str, Any]] | None = None
    _broad_categories: tuple[list[str], dict[str, list[str]]] | None = None
    _genre_labels: Mapping[str, str] | None = None
    _plattenlabels: list[str] | None = None
    _year_floor: int | None = None
    _year_cap: int | None = None

    def _refresh_cache_if_needed(self) -> None:
        """Reload all corpus slices when source files changed or cache is empty."""
        current_mtimes = _corpus_source_mtimes()
        with self._lock:
            if (
                self._source_mtimes is not None
                and self._source_mtimes == current_mtimes
                and self._reviews is not None
            ):
                return
            reviews = list(self.source.reviews())
            metadata = self.source.metadata()
            affinities = list(self.source.affinities())
            affinities_by_review_id = self.source.affinities_by_review_id()
            memberships = self.source.memberships()
            communities = list(self.source.communities())
            broad_categories = self.source.broad_categories()
            genre_labels = self.source.genre_labels()
            plattenlabels = list(self.source.plattenlabels())
            year_floor = self.source.year_floor()
            year_cap = self.source.year_cap()
            self._reviews = reviews
            self._metadata = metadata
            self._affinities = affinities
            self._affinities_by_review_id = affinities_by_review_id
            self._memberships = memberships
            self._communities = communities
            self._broad_categories = broad_categories
            self._genre_labels = genre_labels
            self._plattenlabels = plattenlabels
            self._year_floor = year_floor
            self._year_cap = year_cap
            self._source_mtimes = current_mtimes

    def reviews(self) -> Sequence[Review]:
        """Return cached reviews."""
        self._refresh_cache_if_needed()
        assert self._reviews is not None
        return self._reviews

    def newest_reviews(self, count: int) -> Sequence[Review]:
        """Return cached newest reviews by descending review id."""
        reviews = list(self.reviews())
        reviews.sort(key=lambda review: int(review.id), reverse=True)
        return reviews[: max(1, count)]

    def metadata(self) -> Mapping[int, Mapping[str, Any]]:
        """Return cached metadata keyed by review id."""
        self._refresh_cache_if_needed()
        assert self._metadata is not None
        return self._metadata

    def affinities(self) -> Sequence[Mapping[str, Any]]:
        """Return cached affinity records."""
        self._refresh_cache_if_needed()
        assert self._affinities is not None
        return self._affinities

    def affinities_by_review_id(self) -> Mapping[int, Mapping[str, Any]]:
        """Return cached affinity records keyed by review id."""
        self._refresh_cache_if_needed()
        assert self._affinities_by_review_id is not None
        return self._affinities_by_review_id

    def memberships(self) -> dict[str, dict[str, str]]:
        """Return cached artist-community memberships."""
        self._refresh_cache_if_needed()
        assert self._memberships is not None
        return self._memberships

    def communities(self) -> Sequence[Mapping[str, Any]]:
        """Return cached community metadata."""
        self._refresh_cache_if_needed()
        assert self._communities is not None
        return self._communities

    def broad_categories(self) -> tuple[list[str], dict[str, list[str]]]:
        """Return cached broad categories and community assignments."""
        self._refresh_cache_if_needed()
        assert self._broad_categories is not None
        return self._broad_categories

    def genre_labels(self) -> Mapping[str, str]:
        """Return cached readable community labels."""
        self._refresh_cache_if_needed()
        assert self._genre_labels is not None
        return self._genre_labels

    def plattenlabels(self) -> Sequence[str]:
        """Return cached record labels."""
        self._refresh_cache_if_needed()
        assert self._plattenlabels is not None
        return self._plattenlabels

    def year_floor(self) -> int:
        """Return cached lowest release year."""
        self._refresh_cache_if_needed()
        assert self._year_floor is not None
        return self._year_floor

    def year_cap(self) -> int:
        """Return cached highest release year."""
        self._refresh_cache_if_needed()
        assert self._year_cap is not None
        return self._year_cap

    def artist_mbid_for_review(self, review_id: int) -> str | None:
        """Return the MusicBrainz artist ID for one cached review, if known."""
        self._refresh_cache_if_needed()
        assert self._metadata is not None
        return _artist_mbid_from_metadata(self._metadata, review_id)


def _artist_mbid_from_metadata(
    metadata: Mapping[int, Mapping[str, Any]],
    review_id: int,
) -> str | None:
    """Return a trimmed artist MBID from one metadata row."""
    row = metadata.get(review_id)
    if row is None:
        return None
    artist_mbid = row.get("artist_mbid")
    if not isinstance(artist_mbid, str):
        return None
    trimmed = artist_mbid.strip()
    return trimmed or None


_CACHED_CORPUS_PROVIDER: CachedCorpusProvider | None = None
_ARTIST_IMAGE_SERVICE: ArtistImageService | None = None


def reset_corpus_provider_cache() -> None:
    """Clear the module-level corpus provider singleton (for tests)."""
    global _CACHED_CORPUS_PROVIDER
    _CACHED_CORPUS_PROVIDER = None


def reset_artist_image_service() -> None:
    """Clear the module-level artist image service singleton (for tests)."""
    global _ARTIST_IMAGE_SERVICE
    _ARTIST_IMAGE_SERVICE = None


def get_corpus_provider() -> CorpusProvider:
    """FastAPI dependency for corpus data access."""
    global _CACHED_CORPUS_PROVIDER
    if _CACHED_CORPUS_PROVIDER is None:
        _CACHED_CORPUS_PROVIDER = CachedCorpusProvider(FileCorpusProvider())
    return _CACHED_CORPUS_PROVIDER


def get_user_db() -> sqlite3.Connection:
    """Return a SQLite connection for user/profile endpoints."""
    return get_connection()


def get_optional_user_db(
    authorization: str | None = Header(default=None),
) -> sqlite3.Connection | None:
    """Return a user database only when an auth header is present."""
    if not authorization:
        return None
    return get_connection()


def get_artist_image_service() -> ArtistImageService:
    """FastAPI dependency for artist image lookups."""
    global _ARTIST_IMAGE_SERVICE
    if _ARTIST_IMAGE_SERVICE is None:
        _ARTIST_IMAGE_SERVICE = default_artist_image_service()
    return _ARTIST_IMAGE_SERVICE
