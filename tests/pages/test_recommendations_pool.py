"""Tests for the shared recommendations + archive playlist candidate module."""

from __future__ import annotations

from typing import Any

import pytest
from pages import recommendations_pool

from music_review.domain.models import Review


def _make_review(rid: int, *, artist: str = "Artist", album: str = "Album") -> Review:
    """Build a minimal Review object suitable for tests in this module."""
    return Review(
        id=rid,
        url=f"https://example.com/review/{rid}",
        artist=artist,
        album=album,
        text=f"Review text for {artist} - {album}",
    )


class TestComputeRecommendationsEarlyReturns:
    """``compute_recommendations`` short-circuits when there is nothing to score."""

    def test_returns_empty_when_no_selected_communities(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # No selected_communities in session => no candidates can match.
        monkeypatch.setattr(recommendations_pool.st, "session_state", {})
        monkeypatch.setattr(
            recommendations_pool,
            "get_selected_communities",
            lambda: set(),
        )
        assert recommendations_pool.compute_recommendations() == []

    def test_returns_empty_when_corpus_empty(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # A taste is set but the corpus is missing => return [] gracefully.
        monkeypatch.setattr(
            recommendations_pool.st,
            "session_state",
            {"filter_settings": {}, "community_weights_raw": {"C001": 1.0}},
        )
        monkeypatch.setattr(
            recommendations_pool,
            "get_selected_communities",
            lambda: {"C001"},
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_reviews_and_metadata",
            lambda: ([], {}),
        )
        monkeypatch.setattr(recommendations_pool, "load_affinities", lambda: [])
        monkeypatch.setattr(
            recommendations_pool,
            "load_community_memberships",
            lambda: {},
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_communities_res_10",
            lambda: [],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_genre_labels_res_10",
            lambda: {},
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_sorted_unique_plattenlabels_from_reviews",
            lambda: [],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "max_release_year_from_corpus",
            lambda: 2026,
        )
        monkeypatch.setattr(
            recommendations_pool,
            "min_release_year_from_corpus",
            lambda: 1900,
        )
        assert recommendations_pool.compute_recommendations() == []


class TestArchivePlaylistCandidates:
    """``archive_playlist_candidates`` adapts compute_recommendations output."""

    def test_returns_empty_tuple_when_no_recommendations(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            recommendations_pool,
            "compute_recommendations",
            list,
        )
        reviews, ranked_rows = recommendations_pool.archive_playlist_candidates()
        assert reviews == []
        assert ranked_rows is None

    def test_maps_review_ids_to_review_objects_in_score_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Two reviews exist; recommendations rank them in a specific order.
        review_a = _make_review(101, artist="Alpha")
        review_b = _make_review(202, artist="Beta")

        monkeypatch.setattr(
            recommendations_pool,
            "compute_recommendations",
            lambda: [
                {"review_id": 202, "overall_score": 0.85},
                {"review_id": 101, "overall_score": 0.42},
            ],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_reviews_and_metadata",
            lambda: ([review_a, review_b], {}),
        )

        reviews, ranked_rows = recommendations_pool.archive_playlist_candidates()

        assert [r.id for r in reviews] == [202, 101]
        assert ranked_rows is not None
        assert [row["review"].id for row in ranked_rows] == [202, 101]
        assert [row["overall_score"] for row in ranked_rows] == [0.85, 0.42]

    def test_skips_recommendations_without_resolvable_review(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # The corpus only knows id 101, so the dangling 999 entry is skipped.
        review_a = _make_review(101)
        monkeypatch.setattr(
            recommendations_pool,
            "compute_recommendations",
            lambda: [
                {"review_id": 999, "overall_score": 0.99},
                {"review_id": 101, "overall_score": 0.10},
            ],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_reviews_and_metadata",
            lambda: ([review_a], {}),
        )

        reviews, ranked_rows = recommendations_pool.archive_playlist_candidates()

        assert [r.id for r in reviews] == [101]
        assert ranked_rows is not None
        assert [row["review"].id for row in ranked_rows] == [101]

    def test_returns_empty_when_only_unresolvable_recommendations(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            recommendations_pool,
            "compute_recommendations",
            lambda: [{"review_id": 7, "overall_score": 0.5}],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_reviews_and_metadata",
            lambda: ([_make_review(8)], {}),
        )
        reviews, ranked_rows = recommendations_pool.archive_playlist_candidates()
        assert reviews == []
        assert ranked_rows is None

    def test_ranked_rows_shape_matches_build_album_weights(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # ``build_album_weights`` expects each row to expose ``review`` (a Review)
        # and ``overall_score`` (a float). Smoke-test the shape with the real
        # downstream function.
        from music_review.dashboard.newest_spotify_playlist import build_album_weights

        review_a = _make_review(1)
        review_b = _make_review(2)
        monkeypatch.setattr(
            recommendations_pool,
            "compute_recommendations",
            lambda: [
                {"review_id": 1, "overall_score": 0.4},
                {"review_id": 2, "overall_score": 0.6},
            ],
        )
        monkeypatch.setattr(
            recommendations_pool,
            "load_reviews_and_metadata",
            lambda: ([review_a, review_b], {}),
        )
        reviews, ranked_rows = recommendations_pool.archive_playlist_candidates()
        chosen, weights, raw = build_album_weights(reviews, ranked_rows)
        assert {r.id for r in chosen} == {1, 2}
        assert sum(weights) == pytest.approx(1.0)
        assert all(value >= 0.0 for value in raw)


class TestSortModeConstantsAreReExported:
    """Empfehlungen page imports these constants from the shared module."""

    def test_sort_mode_constants_have_expected_values(self) -> None:
        assert recommendations_pool.SORT_MODE_FIXED == "Feste Reihenfolge"
        assert recommendations_pool.SORT_MODE_RANDOM == "Mit Zufall"

    def test_sort_mode_migration_translates_legacy_keys(self) -> None:
        migration: dict[str, Any] = recommendations_pool.SORT_MODE_MIGRATION
        assert migration["Deterministisch"] == recommendations_pool.SORT_MODE_FIXED
        assert migration["Serendipity"] == recommendations_pool.SORT_MODE_RANDOM
