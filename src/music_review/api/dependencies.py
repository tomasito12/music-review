"""Data providers and dependency hooks for the HTTP API."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from fastapi import Header

from music_review.dashboard.user_db import get_connection
from music_review.data_access.affinities import affinities_by_review_id, affinities_list
from music_review.data_access.communities import (
    load_artist_communities,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
)
from music_review.data_access.metadata import load_metadata_map
from music_review.data_access.paths import reviews_path
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


def get_corpus_provider() -> CorpusProvider:
    """FastAPI dependency for corpus data access."""
    return FileCorpusProvider()


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
