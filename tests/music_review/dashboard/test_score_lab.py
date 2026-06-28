"""Tests for Score Lab row builder and CSV export."""

from __future__ import annotations

from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.application.presets import get_preset
from music_review.application.recommendation_service import (
    RecommendationInputs,
    RecommendationService,
)
from music_review.dashboard.score_lab import (
    SCORE_LAB_TABLE_COLUMNS,
    affinity_by_review_id,
    build_score_lab_rows,
    diagnose_score_lab_empty,
    guess_matching_preset_id,
    k_hits_for_review,
    parse_review_ids_text,
    profile_for_archive_lab,
    profile_with_lab_overrides,
    score_lab_rows_to_csv,
)
from music_review.domain.models import Review


def _review(
    review_id: int,
    *,
    artist: str = "Artist",
    rating: float | None = 8.0,
    release_year: int = 2020,
    labels: list[str] | None = None,
) -> Review:
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
    return {
        "review_id": review_id,
        "communities": {
            "res_10": [
                {"id": community_id, "score": score} for community_id, score in entries
            ],
        },
    }


def _inputs() -> RecommendationInputs:
    reviews = [
        _review(1, artist="Strong", rating=9, labels=["Sub Pop"]),
        _review(2, artist="Weak", rating=7, labels=["Matador"]),
        _review(3, artist="Filtered", rating=5, labels=["Sub Pop"]),
    ]
    return RecommendationInputs(
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


def _profile(**kwargs: object) -> TasteProfile:
    defaults: dict[str, object] = {
        "selected_communities": ("C001",),
        "community_weights_raw": {"C001": 1.0},
        "filter_settings": TasteFilterSettings(score_min=0.0, rating_min=6),
    }
    defaults.update(kwargs)
    return TasteProfile(**defaults)  # type: ignore[arg-type]


def test_parse_review_ids_text_ignores_invalid_tokens() -> None:
    assert parse_review_ids_text("1, 2; bad, 3") == frozenset({1, 2, 3})
    assert parse_review_ids_text("") == frozenset()


def test_guess_matching_preset_id_detects_balanced() -> None:
    preset = get_preset("balanced")
    assert guess_matching_preset_id(preset.filter_settings) == "balanced"


def test_profile_with_lab_overrides_forces_deterministic_sort() -> None:
    profile = _profile(
        filter_settings=TasteFilterSettings(
            sort_mode="discovery",
            serendipity=0.8,
            overall_weight_alpha=0.2,
        ),
    )
    updated = profile_with_lab_overrides(
        profile,
        overall_weight_alpha=0.7,
        overall_weight_beta=0.2,
        overall_weight_gamma=0.1,
        community_spectrum_crossover=0.4,
        score_min=0.1,
        score_max=0.9,
    )
    assert updated.filter_settings.sort_mode == "deterministic"
    assert updated.filter_settings.serendipity == 0.0
    assert updated.filter_settings.overall_weight_alpha == 0.7


def test_build_score_lab_rows_archive_contains_table_columns() -> None:
    rows = build_score_lab_rows(_profile(), _inputs(), limit=10)
    assert len(rows) == 3
    assert rows[0]["rank"] == 1
    for column in SCORE_LAB_TABLE_COLUMNS:
        assert column in rows[0]
    assert rows[0]["artist"] == "Strong"
    assert rows[0]["k_hits"] == 1


def test_build_score_lab_rows_respects_limit() -> None:
    rows = build_score_lab_rows(_profile(), _inputs(), limit=1)
    assert len(rows) == 1


def test_build_score_lab_rows_review_ids_mode_without_archive_filters() -> None:
    profile = _profile(
        filter_settings=TasteFilterSettings(
            score_min=0.0,
            score_max=1.0,
            rating_min=8,
        ),
    )
    rows = build_score_lab_rows(
        profile,
        _inputs(),
        data_source="review_ids",
        review_ids=frozenset({2, 3}),
        limit=None,
    )
    review_ids = {row["review_id"] for row in rows}
    assert review_ids == {2, 3}


def test_build_score_lab_rows_live_alpha_changes_overall_score() -> None:
    base_profile = _profile(
        filter_settings=TasteFilterSettings(
            score_min=0.0,
            rating_min=6,
            overall_weight_alpha=0.1,
            overall_weight_beta=0.8,
            overall_weight_gamma=0.1,
        ),
    )
    tuned_profile = profile_with_lab_overrides(
        base_profile,
        overall_weight_alpha=0.9,
        overall_weight_beta=0.05,
        overall_weight_gamma=0.05,
        community_spectrum_crossover=0.5,
        score_min=0.0,
        score_max=1.0,
    )
    base_rows = build_score_lab_rows(base_profile, _inputs(), limit=1)
    tuned_rows = build_score_lab_rows(tuned_profile, _inputs(), limit=1)
    assert base_rows[0]["overall_score"] != tuned_rows[0]["overall_score"]


def test_score_lab_rows_to_csv_uses_table_columns() -> None:
    rows = build_score_lab_rows(_profile(), _inputs(), limit=1)
    csv_text = score_lab_rows_to_csv(rows)
    header = csv_text.splitlines()[0]
    assert header == ";".join(SCORE_LAB_TABLE_COLUMNS)
    assert "Strong" in csv_text


def test_k_hits_for_review_counts_positive_selected_communities() -> None:
    aff = _affinity(1, ("C001", 0.5), ("C002", 0.0))
    assert k_hits_for_review(aff, selected_comms={"C001", "C002"}) == 1


def test_affinity_by_review_id_indexes_rows() -> None:
    affinities = [_affinity(1), _affinity(2)]
    indexed = affinity_by_review_id(affinities)
    assert set(indexed) == {1, 2}


def test_build_score_lab_rows_empty_without_selected_communities() -> None:
    profile = TasteProfile(selected_communities=())
    assert build_score_lab_rows(profile, _inputs()) == []


def test_archive_rows_match_service_order_with_product_filters() -> None:
    profile = _profile()
    inputs = _inputs()
    service = RecommendationService(inputs)
    service_rows = service.compute_archive_recommendations(profile)
    lab_rows = build_score_lab_rows(
        profile,
        inputs,
        limit=None,
        apply_product_filters=True,
    )
    assert [row["review_id"] for row in lab_rows] == [
        row["review_id"] for row in service_rows
    ]


def test_relaxed_archive_mode_includes_low_score_matches() -> None:
    profile = _profile(
        filter_settings=TasteFilterSettings(score_min=0.8, rating_min=6),
    )
    strict = build_score_lab_rows(
        profile,
        _inputs(),
        apply_product_filters=True,
        limit=None,
    )
    relaxed = build_score_lab_rows(
        profile,
        _inputs(),
        apply_product_filters=False,
        limit=None,
    )
    assert len(relaxed) >= len(strict)
    assert len(relaxed) > 0


def test_diagnose_score_lab_empty_reports_pipeline_counts() -> None:
    profile = _profile()
    counts = diagnose_score_lab_empty(
        profile,
        _inputs(),
        apply_product_filters=False,
    )
    assert counts["community_hits"] >= counts["after_score_range"]
    assert counts["after_product_filters"] > 0


def test_profile_for_archive_lab_relaxes_non_score_filters() -> None:
    profile = _profile(
        filter_settings=TasteFilterSettings(
            rating_min=8,
            year_min=2020,
            plattenlabel_selection=("Sub Pop",),
        ),
    )
    relaxed = profile_for_archive_lab(profile, apply_product_filters=False)
    assert relaxed.filter_settings.rating_min == 0.0
    assert relaxed.filter_settings.plattenlabel_selection is None
