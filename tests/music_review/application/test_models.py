"""Tests for application-level profile and response models."""

from __future__ import annotations

from music_review.application.models import (
    ExplanationSignals,
    PlaylistExport,
    PlaylistExportItem,
    Recommendation,
    RecommendationSet,
    TasteFilterSettings,
    TasteProfile,
)


def test_filter_settings_normalizes_ranges_and_legacy_sort_mode() -> None:
    """Stored filter values are clamped into the API model's supported ranges."""
    settings = TasteFilterSettings.from_mapping(
        {
            "year_min": 2025,
            "year_max": 1999,
            "rating_min": 12,
            "rating_max": -2,
            "score_min": 1.2,
            "score_max": -0.5,
            "community_spectrum_crossover": 9,
            "overall_weight_alpha": 2,
            "overall_weight_beta": -1,
            "overall_weight_gamma": "not-a-number",
            "plattenlabel_selection": ["Sub Pop", "", "Matador"],
            "sort_mode": "Mit Zufall",
            "serendipity": 4,
        },
    )

    assert settings.year_min == 1999
    assert settings.year_max == 2025
    assert settings.rating_min == 0
    assert settings.rating_max == 10
    assert settings.score_min == 0
    assert settings.score_max == 1
    assert settings.community_spectrum_crossover == 1
    assert settings.overall_weight_alpha == 1
    assert settings.overall_weight_beta == 0
    assert settings.overall_weight_gamma == 0.25
    assert settings.plattenlabel_selection == ("Sub Pop", "Matador")
    assert settings.sort_mode == "discovery"
    assert settings.serendipity == 1


def test_profile_from_legacy_payload_keeps_taste_fields() -> None:
    """Legacy Streamlit profile payloads become API-level taste profiles."""
    profile = TasteProfile.from_mapping(
        {
            "profile_name": "mein-profil",
            "flow_mode": "artist",
            "selected_communities": {"C002", "C001"},
            "artist_flow_selected_communities": ["C001"],
            "genre_flow_selected_communities": ["C002"],
            "community_weights_raw": {"C001": "0.8", "C002": 0.4, "bad": "x"},
            "filter_settings": {"score_min": 0.4, "rating_min": 6},
        },
    )

    assert profile.name == "mein-profil"
    assert profile.flow_mode == "artist"
    assert profile.selected_communities == ("C001", "C002")
    assert profile.artist_flow_selected_communities == ("C001",)
    assert profile.genre_flow_selected_communities == ("C002",)
    assert profile.community_weights_raw == {"C001": 0.8, "C002": 0.4}
    assert profile.filter_settings.score_min == 0.4
    assert profile.filter_settings.rating_min == 6


def test_profile_to_dict_is_json_ready() -> None:
    """Profile collections are emitted as JSON-friendly lists and dicts."""
    profile = TasteProfile(
        id="profile_1",
        user_id="user_1",
        selected_communities=("C001",),
        community_weights_raw={"C001": 0.6},
        filter_settings=TasteFilterSettings(score_min=0.5),
    )

    payload = profile.to_dict()

    assert payload["id"] == "profile_1"
    assert payload["user_id"] == "user_1"
    assert payload["selected_communities"] == ["C001"]
    assert payload["community_weights_raw"] == {"C001": 0.6}
    assert payload["filter_settings"]["score_min"] == 0.5


def test_recommendation_set_to_dict_contains_pagination_fields() -> None:
    """Recommendation responses expose pagination metadata for the frontend."""
    recommendation = Recommendation(
        rank=1,
        review_id=42,
        artist="Artist",
        album="Album",
        overall_score=0.9,
        explanation_signals=ExplanationSignals(
            matched_community_count=2,
            primary_matched_labels=("Indie Rock",),
            fit_level="high",
        ),
    )
    result = RecommendationSet(
        source="archive",
        total=100,
        limit=25,
        offset=0,
        items=(recommendation,),
        generated_at="2026-06-22T12:00:00Z",
    )

    payload = result.to_dict()

    assert payload["source"] == "archive"
    assert payload["total"] == 100
    assert payload["limit"] == 25
    assert payload["offset"] == 0
    assert payload["items"][0]["explanation_signals"]["fit_level"] == "high"


def test_playlist_export_to_dict_is_transient_response() -> None:
    """Playlist exports return file content without requiring persistence fields."""
    export = PlaylistExport(
        source="new_reviews",
        name="Plattenradar",
        format="txt",
        filename="plattenradar.txt",
        content_type="text/plain",
        content="Artist - Track",
        items=(
            PlaylistExportItem(
                review_id=1,
                artist="Artist",
                album="Album",
                track_title="Track",
                source_kind="highlight",
                score_weight=1.0,
                raw_score=0.8,
            ),
        ),
    )

    payload = export.to_dict()

    assert payload["source"] == "new_reviews"
    assert payload["filename"] == "plattenradar.txt"
    assert payload["content"] == "Artist - Track"
    assert payload["items"][0]["track_title"] == "Track"
