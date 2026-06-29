"""Tests for API dependency providers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from music_review.api.dependencies import (
    CachedCorpusProvider,
    FileCorpusProvider,
    _artist_mbid_from_metadata,
    get_corpus_provider,
    reset_corpus_provider_cache,
)
from music_review.domain.models import Review


def _review(review_id: int) -> Review:
    return Review(
        id=review_id,
        artist="Artist",
        album="Album",
        text="Review text",
        rating=8,
        url=f"https://example.com/{review_id}",
    )


@pytest.fixture(autouse=True)
def _reset_provider_singleton() -> None:
    """Ensure corpus provider tests do not share singleton state."""
    reset_corpus_provider_cache()


def test_cached_corpus_provider_loads_reviews_only_once() -> None:
    """Repeated review access should not reload from disk."""
    source = MagicMock(spec=FileCorpusProvider)
    source.reviews.return_value = [_review(1)]
    source.metadata.return_value = {}
    source.affinities.return_value = []
    source.affinities_by_review_id.return_value = {}
    source.memberships.return_value = {}
    source.communities.return_value = []
    source.broad_categories.return_value = ([], {})
    source.genre_labels.return_value = {}
    source.plattenlabels.return_value = []
    source.year_floor.return_value = 1990
    source.year_cap.return_value = 2024

    with patch(
        "music_review.api.dependencies._corpus_source_mtimes",
        return_value=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
    ):
        provider = CachedCorpusProvider(source)
        first = provider.reviews()
        second = provider.reviews()

    assert first == second
    source.reviews.assert_called_once()


def test_cached_corpus_provider_refreshes_when_source_files_change() -> None:
    """A changed source mtime should trigger a corpus reload."""
    source = MagicMock(spec=FileCorpusProvider)
    source.reviews.side_effect = [[_review(1)], [_review(2)]]
    source.metadata.return_value = {}
    source.affinities.return_value = []
    source.affinities_by_review_id.return_value = {}
    source.memberships.return_value = {}
    source.communities.return_value = []
    source.broad_categories.return_value = ([], {})
    source.genre_labels.return_value = {}
    source.plattenlabels.return_value = []
    source.year_floor.return_value = 1990
    source.year_cap.return_value = 2024

    mtimes = iter(
        [
            (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
            (9.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
        ],
    )

    with patch(
        "music_review.api.dependencies._corpus_source_mtimes",
        side_effect=lambda: next(mtimes),
    ):
        provider = CachedCorpusProvider(source)
        first = provider.reviews()
        second = provider.reviews()

    assert first[0].id == 1
    assert second[0].id == 2
    assert source.reviews.call_count == 2


def test_cached_corpus_provider_handles_concurrent_access() -> None:
    """Parallel readers should not observe a half-built corpus cache."""
    source = MagicMock(spec=FileCorpusProvider)
    source.reviews.return_value = [_review(1)]
    source.metadata.return_value = {}
    source.affinities.return_value = []
    source.affinities_by_review_id.return_value = {}
    source.memberships.return_value = {}
    source.communities.return_value = [{"id": "C001"}]
    source.broad_categories.return_value = ([], {})
    source.genre_labels.return_value = {"C001": "Indie Rock"}
    source.plattenlabels.return_value = []
    source.year_floor.return_value = 1990
    source.year_cap.return_value = 2024

    with patch(
        "music_review.api.dependencies._corpus_source_mtimes",
        return_value=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
    ):
        provider = CachedCorpusProvider(source)

        def read_labels() -> str:
            return provider.genre_labels()["C001"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: read_labels(), range(32)))

    assert results == ["Indie Rock"] * 32


def test_get_corpus_provider_returns_singleton_instance() -> None:
    """Dependency accessor should reuse one cached provider instance."""
    first = get_corpus_provider()
    second = get_corpus_provider()
    assert first is second


def test_artist_mbid_from_metadata_returns_trimmed_value() -> None:
    """Metadata lookup returns a trimmed artist MBID when present."""
    metadata = {
        1: {"artist_mbid": "  mbid-1  "},
        2: {"artist_mbid": ""},
        3: {"artist": "No MBID"},
    }

    assert _artist_mbid_from_metadata(metadata, 1) == "mbid-1"
    assert _artist_mbid_from_metadata(metadata, 2) is None
    assert _artist_mbid_from_metadata(metadata, 3) is None
    assert _artist_mbid_from_metadata(metadata, 99) is None
