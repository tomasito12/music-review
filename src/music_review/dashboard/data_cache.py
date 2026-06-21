"""Streamlit cache wrappers over framework-agnostic data_access loaders."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from music_review.dashboard.cache_keys import FileCacheSignature, file_cache_signature
from music_review.data_access.affinities import (
    affinities_by_review_id,
    affinities_list,
    top_communities_per_review,
)
from music_review.data_access.communities import (
    load_artist_communities,
    load_broad_categories_res_10,
    load_communities_res_10,
    load_genre_labels_res_10,
)
from music_review.data_access.metadata import load_metadata_map, resolve_metadata_path
from music_review.data_access.paths import (
    album_community_affinities_path,
    communities_res_10_path,
    community_broad_categories_res_10_path,
    community_genre_labels_res_10_path,
    community_memberships_path,
    reviews_path,
)
from music_review.data_access.reviews import (
    YEAR_SLIDER_FALLBACK_FLOOR,
    load_reviews,
    max_release_year_in_jsonl,
    min_release_year_in_jsonl,
    plattenlabel_album_count_buckets_from_reviews_jsonl,
    unique_plattenlabels_from_reviews_jsonl,
)
from music_review.domain.models import Review

# Corpus data changes slowly; newest-reviews slice refreshes more often.
CACHE_TTL_CORPUS = 3600
CACHE_TTL_NEWEST_SLICE = 300


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_communities_res_10_cached(
    signature: FileCacheSignature,
) -> list[dict[str, Any]]:
    """Cached resolution-10 communities."""
    return load_communities_res_10()


def cached_load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities with top artists (cached)."""
    path = communities_res_10_path()
    return _load_communities_res_10_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_genre_labels_res_10_cached(
    signature: FileCacheSignature,
) -> dict[str, str]:
    """Cached LLM genre labels for communities (res_10)."""
    return load_genre_labels_res_10()


def cached_load_genre_labels_res_10() -> dict[str, str]:
    """Load LLM-assigned genre labels for communities (res_10, cached)."""
    path = community_genre_labels_res_10_path()
    return _load_genre_labels_res_10_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_broad_categories_res_10_cached(
    signature: FileCacheSignature,
) -> tuple[list[str], dict[str, list[str]]]:
    """Cached broad categories and per-community mappings."""
    return load_broad_categories_res_10()


def cached_load_broad_categories_res_10() -> tuple[list[str], dict[str, list[str]]]:
    """Load broad categories and per-community mappings (cached)."""
    path = community_broad_categories_res_10_path()
    return _load_broad_categories_res_10_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_community_memberships_cached(
    signature: FileCacheSignature,
) -> dict[str, dict[str, str]]:
    """Cached artist -> community memberships."""
    return load_artist_communities()


def cached_load_community_memberships() -> dict[str, dict[str, str]]:
    """Load artist community memberships (cached)."""
    path = community_memberships_path()
    return _load_community_memberships_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _max_release_year_from_corpus_cached(
    signature: FileCacheSignature,
) -> int:
    """Upper bound for year sliders: max year in corpus or current year."""
    m = max_release_year_in_jsonl(reviews_path())
    if m is None:
        return datetime.now().year
    return m


def cached_max_release_year_from_corpus() -> int:
    """Upper bound for year sliders (cached)."""
    path = reviews_path()
    return _max_release_year_from_corpus_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _min_release_year_from_corpus_cached(
    signature: FileCacheSignature,
) -> int:
    """Lower bound for year sliders: min year in corpus or fallback."""
    m = min_release_year_in_jsonl(reviews_path())
    if m is None:
        return YEAR_SLIDER_FALLBACK_FLOOR
    return m


def cached_min_release_year_from_corpus() -> int:
    """Lower bound for year sliders (cached)."""
    path = reviews_path()
    return _min_release_year_from_corpus_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_plattenlabel_filter_buckets_cached(
    signature: FileCacheSignature,
) -> tuple[list[str], list[str], int]:
    """Cached Plattenlabel buckets from reviews corpus."""
    return plattenlabel_album_count_buckets_from_reviews_jsonl(reviews_path())


def cached_load_plattenlabel_filter_buckets() -> tuple[list[str], list[str], int]:
    """Cached head/tail Plattenlabel buckets from reviews corpus."""
    path = reviews_path()
    return _load_plattenlabel_filter_buckets_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_sorted_unique_plattenlabels_cached(
    signature: FileCacheSignature,
) -> list[str]:
    """Cached sorted unique Plattenlabels from reviews corpus."""
    return unique_plattenlabels_from_reviews_jsonl(reviews_path())


def cached_load_sorted_unique_plattenlabels() -> list[str]:
    """Load sorted unique Plattenlabels from reviews corpus (cached)."""
    path = reviews_path()
    return _load_sorted_unique_plattenlabels_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_reviews_and_metadata_cached(
    reviews_signature: FileCacheSignature,
    metadata_signature: FileCacheSignature,
) -> tuple[list[Review], dict[int, dict[str, Any]]]:
    """Load corpus reviews plus optional imputed metadata map."""
    return load_reviews(), load_metadata_map()


def cached_load_reviews_and_metadata() -> tuple[
    list[Review],
    dict[int, dict[str, Any]],
]:
    """Load corpus reviews and metadata map (cached)."""
    reviews_p = reviews_path()
    metadata_p = resolve_metadata_path()
    return _load_reviews_and_metadata_cached(
        file_cache_signature(reviews_p),
        file_cache_signature(metadata_p),
    )


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_affinities_list_cached(
    signature: FileCacheSignature,
) -> list[dict[str, Any]]:
    """Cached album-to-community affinity records as a list."""
    return affinities_list()


def cached_load_affinities_list() -> list[dict[str, Any]]:
    """Load album affinity records used for scoring (cached list form)."""
    path = album_community_affinities_path()
    return _load_affinities_list_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_affinities_by_review_id_cached(
    signature: FileCacheSignature,
) -> dict[int, dict[str, Any]]:
    """Cached album affinities keyed by review_id."""
    return affinities_by_review_id()


def cached_load_affinities_by_review_id() -> dict[int, dict[str, Any]]:
    """Load album affinities keyed by review_id (cached)."""
    path = album_community_affinities_path()
    return _load_affinities_by_review_id_cached(file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_CORPUS)
def _load_affinity_top_map_cached(
    signature: FileCacheSignature,
    *,
    top_k: int = 5,
) -> dict[int, list[tuple[str, float]]]:
    """Cached top-k communities per review for one resolution."""
    return top_communities_per_review(top_k=top_k)


def cached_load_affinity_top_map(
    *,
    top_k: int = 5,
) -> dict[int, list[tuple[str, float]]]:
    """Load top-k community affinities per review (cached)."""
    path = album_community_affinities_path()
    return _load_affinity_top_map_cached(file_cache_signature(path), top_k=top_k)


@st.cache_data(ttl=CACHE_TTL_NEWEST_SLICE)
def _load_newest_reviews_cached(
    n: int,
    signature: FileCacheSignature,
) -> list[Review]:
    """Return the n newest reviews by id."""
    reviews = load_reviews()
    reviews.sort(key=lambda r: int(r.id), reverse=True)
    return reviews[: max(1, n)]


def cached_load_newest_reviews_slice(n: int) -> list[Review]:
    """Return the n newest reviews by id (cached)."""
    path = reviews_path()
    return _load_newest_reviews_cached(max(1, n), file_cache_signature(path))


@st.cache_data(ttl=CACHE_TTL_NEWEST_SLICE)
def _load_all_reviews_for_breadth_norm_cached(
    signature: FileCacheSignature,
) -> list[Review]:
    """Full corpus for global coverage percentile (breadth_norm)."""
    return load_reviews()


def cached_load_all_reviews_for_breadth_norm() -> list[Review]:
    """Load full review corpus for breadth normalization (cached)."""
    path = reviews_path()
    return _load_all_reviews_for_breadth_norm_cached(file_cache_signature(path))
