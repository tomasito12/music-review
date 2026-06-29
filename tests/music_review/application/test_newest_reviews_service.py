"""Tests for the Streamlit-independent newest-review ranking service."""

from __future__ import annotations

import pytest

from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.application.newest_reviews_service import (
    NewestReviewsInputs,
    NewestReviewsService,
)
from music_review.domain.models import Review


def _review(review_id: int, *, artist: str, rating: float = 8.0) -> Review:
    """Build a minimal review for newest-review service tests."""
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=artist,
        album=f"Album {review_id}",
        text=f"{artist} review text",
        rating=rating,
        release_year=2024,
    )


def _affinity(review_id: int, *entries: tuple[str, float]) -> dict[str, object]:
    """Build a res_10 affinity row."""
    return {
        "review_id": review_id,
        "communities": {
            "res_10": [
                {"id": community_id, "score": score} for community_id, score in entries
            ],
        },
    }


def _service() -> NewestReviewsService:
    """Return a service with a tiny newest-review batch."""
    newest_reviews = [
        _review(1, artist="Pure", rating=9),
        _review(2, artist="Mixed", rating=9),
    ]
    inputs = NewestReviewsInputs(
        newest_reviews=newest_reviews,
        affinity_by_review_id={
            1: _affinity(1, ("C001", 1.0)),
            2: _affinity(2, ("C001", 0.5), ("C003", 0.5)),
        },
        memberships={},
    )
    return NewestReviewsService(inputs)


def test_newest_reviews_without_communities_returns_none() -> None:
    """No selected taste communities means callers can use uniform weights."""
    rows = _service().compute_ranked_rows(TasteProfile())

    assert rows is None


def test_newest_reviews_rank_without_streamlit_state() -> None:
    """The service ranks a newest-review batch from an explicit taste profile."""
    profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
        filter_settings=TasteFilterSettings(rating_min=6),
    )

    rows = _service().compute_ranked_rows(profile)

    assert rows is not None
    assert [row["review_id"] for row in rows] == [1, 2]
    assert rows[0]["review"].artist == "Pure"
    assert rows[0]["score"] > rows[1]["score"]


def test_newest_reviews_breadth_norm_uses_global_percentile_map() -> None:
    """Corpus-wide percentile norms drive album_style_breadth in ranked rows."""
    profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
    )

    rows = _service().compute_ranked_rows(
        profile,
        global_breadth_norm={1: 0.25, 2: 0.75},
    )

    assert rows is not None
    breadth_by_id = {int(row["review_id"]): row["breadth_norm"] for row in rows}
    album_breadth_by_id = {
        int(row["review_id"]): row["album_style_breadth"] for row in rows
    }
    assert breadth_by_id == album_breadth_by_id
    assert breadth_by_id[1] == pytest.approx(0.25)
    assert breadth_by_id[2] == pytest.approx(0.75)
