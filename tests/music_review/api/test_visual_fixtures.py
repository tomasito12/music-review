"""Tests for the visual API fixture app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from music_review.api.visual_fixtures import create_visual_app

_PROFILE = {
    "selected_communities": ["C001", "C002", "C003"],
    "community_weights_raw": {"C001": 0.5, "C002": 0.5, "C003": 0.5},
    "filter_settings": {
        "rating_min": 6,
        "rating_max": 10,
        "score_min": 0.0,
        "score_max": 1,
        "overall_weight_alpha": 0.5,
        "overall_weight_beta": 0.25,
        "overall_weight_gamma": 0.25,
        "community_spectrum_crossover": 0.5,
        "sort_mode": "deterministic",
        "serendipity": 0,
    },
}


def test_visual_app_serves_recommendations_and_artist_images() -> None:
    client = TestClient(create_visual_app())

    health = client.get("/health")
    assert health.status_code == 200

    archive = client.post(
        "/v1/recommendations/archive",
        json={"profile": _PROFILE, "limit": 12, "offset": 0},
    )
    assert archive.status_code == 200
    assert len(archive.json()["items"]) >= 12

    newest = client.post(
        "/v1/recommendations/new-reviews",
        json={"profile": _PROFILE, "limit": 8, "offset": 0, "newest_count": 8},
    )
    assert newest.status_code == 200
    newest_artists = {item["artist"] for item in newest.json()["items"]}
    assert len(newest_artists) == 8
    assert "The Notwist" in newest_artists
    assert "Big Thief" in newest_artists

    images = client.post(
        "/v1/artists/images",
        json={
            "artists": [
                {"artist_mbid": "mbid-notwist", "artist_name": "The Notwist"},
                {"artist_mbid": "mbid-missing", "artist_name": "Missing"},
            ],
        },
    )
    assert images.status_code == 200
    payload = images.json()
    assert payload["items"][0]["image"] is not None
    assert payload["items"][1]["image"] is None
