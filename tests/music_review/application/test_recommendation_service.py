"""Tests for the Streamlit-independent archive recommendation service."""

from __future__ import annotations

from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.application.recommendation_service import (
    RecommendationInputs,
    RecommendationService,
    selected_communities_from_profile,
)
from music_review.domain.models import Review


def _review(
    review_id: int,
    *,
    artist: str,
    rating: float | None = 8.0,
    release_year: int = 2020,
    labels: list[str] | None = None,
) -> Review:
    """Build a minimal review for service tests."""
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=artist,
        album=f"Album {review_id}",
        text=f"{artist} review text",
        rating=rating,
        release_year=release_year,
        labels=labels or [],
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


def _service() -> RecommendationService:
    """Return a service with a tiny deterministic corpus."""
    reviews = [
        _review(1, artist="Strong", rating=9, labels=["Sub Pop"]),
        _review(2, artist="Weak", rating=7, labels=["Matador"]),
        _review(3, artist="Filtered", rating=5, labels=["Sub Pop"]),
    ]
    inputs = RecommendationInputs(
        reviews=reviews,
        metadata={1: {"labels": ["Metadata Label"]}},
        affinities=[
            _affinity(1, ("C001", 0.9), ("C002", 0.2)),
            _affinity(2, ("C001", 0.4)),
            _affinity(3, ("C001", 0.95)),
        ],
        memberships={},
        communities=[
            {"id": "C001", "centroid": "Fallback Rock"},
            {"id": "C002", "centroid": "Fallback Pop"},
        ],
        genre_labels={"C001": "Indie Rock"},
        plattenlabels=["Sub Pop", "Matador"],
        year_floor=1999,
        year_cap=2026,
    )
    return RecommendationService(inputs)


def test_selected_communities_prefers_canonical_profile_field() -> None:
    """Canonical selected communities win over legacy split flow fields."""
    profile = TasteProfile(
        selected_communities=("C001",),
        artist_flow_selected_communities=("C999",),
        genre_flow_selected_communities=("C998",),
    )

    assert selected_communities_from_profile(profile) == {"C001"}


def test_selected_communities_falls_back_to_split_flow_fields() -> None:
    """Legacy artist/genre flow fields still form a usable profile."""
    profile = TasteProfile(
        artist_flow_selected_communities=("C001",),
        genre_flow_selected_communities=("C002",),
    )

    assert selected_communities_from_profile(profile) == {"C001", "C002"}


def test_archive_recommendations_filter_and_sort_without_streamlit() -> None:
    """The service ranks archive recommendations from an explicit taste profile."""
    profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
        filter_settings=TasteFilterSettings(score_min=0.0, rating_min=6),
    )

    rows = _service().compute_archive_recommendations(profile)

    assert [row["review_id"] for row in rows] == [1, 2]
    assert rows[0]["artist"] == "Strong"
    assert rows[1]["artist"] == "Weak"
    assert rows[0]["labels"] == "Metadata Label"
    assert rows[0]["top_communities"][0]["label"] == "Indie Rock"


def test_archive_recommendations_apply_score_and_label_filters() -> None:
    """Hard filters come from the profile settings instead of Streamlit state."""
    service = RecommendationService(
        RecommendationInputs(
            reviews=[
                _review(1, artist="Balanced", rating=9, labels=["Sub Pop"]),
                _review(2, artist="Skewed", rating=9, labels=["Sub Pop"]),
                _review(3, artist="Filtered", rating=5, labels=["Sub Pop"]),
            ],
            metadata={},
            affinities=[
                _affinity(1, ("C001", 1.0)),
                _affinity(2, ("C001", 0.5), ("C003", 0.5)),
                _affinity(3, ("C001", 0.95)),
            ],
            memberships={},
            communities=[
                {"id": "C001", "centroid": "Rock"},
                {"id": "C002", "centroid": "Pop"},
            ],
            genre_labels={},
            plattenlabels=["Sub Pop", "Matador"],
            year_floor=1999,
            year_cap=2026,
        ),
    )
    profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
        filter_settings=TasteFilterSettings(
            score_min=0.8,
            rating_min=6,
            plattenlabel_selection=("Sub Pop",),
        ),
    )

    rows = service.compute_archive_recommendations(profile)

    assert [row["review_id"] for row in rows] == [1]


def test_archive_recommendations_reorder_when_gamma_weight_changes() -> None:
    """Higher gamma weight should prefer stylistically broader albums."""
    service = RecommendationService(
        RecommendationInputs(
            reviews=[
                _review(1, artist="Pure", rating=8),
                _review(2, artist="Mixed", rating=8),
            ],
            metadata={},
            affinities=[
                _affinity(1, ("C001", 1.0)),
                _affinity(2, ("C001", 0.5), ("C002", 0.5)),
            ],
            memberships={},
            communities=[
                {"id": "C001", "centroid": "Rock"},
                {"id": "C002", "centroid": "Pop"},
            ],
            genre_labels={},
            plattenlabels=[],
            year_floor=1999,
            year_cap=2026,
        ),
    )
    fit_profile = TasteProfile(
        selected_communities=("C001",),
        community_weights_raw={"C001": 1.0},
        filter_settings=TasteFilterSettings(
            score_min=0.0,
            rating_min=6,
            overall_weight_alpha=1.0,
            overall_weight_beta=0.0,
            overall_weight_gamma=0.0,
        ),
    )
    breadth_profile = fit_profile.model_copy(
        update={
            "filter_settings": fit_profile.filter_settings.model_copy(
                update={
                    "overall_weight_alpha": 0.0,
                    "overall_weight_beta": 0.0,
                    "overall_weight_gamma": 1.0,
                },
            ),
        },
    )

    fit_rows = service.compute_archive_recommendations(fit_profile)
    breadth_rows = service.compute_archive_recommendations(breadth_profile)

    assert fit_rows[0]["review_id"] == 1
    assert breadth_rows[0]["review_id"] == 2
    assert fit_rows[0]["album_style_breadth"] < breadth_rows[0]["album_style_breadth"]
