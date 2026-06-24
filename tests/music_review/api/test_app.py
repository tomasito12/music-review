"""Tests for the FastAPI v1 boundary."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from music_review.api.app import create_app
from music_review.api.dependencies import (
    get_corpus_provider,
    get_optional_user_db,
    get_user_db,
)
from music_review.dashboard.user_db import get_connection
from music_review.domain.models import Review, Track


class FakeCorpusProvider:
    """Small in-memory corpus for API endpoint tests."""

    def __init__(self) -> None:
        """Build a tiny corpus with affinities and tracklists."""
        self._reviews = [
            _review(1, artist="Alpha", album="First", track_title="Spark", rating=9),
            _review(2, artist="Beta", album="Second", track_title="Drift", rating=7),
        ]

    def reviews(self) -> Sequence[Review]:
        """Return the fake review corpus."""
        return self._reviews

    def newest_reviews(self, count: int) -> Sequence[Review]:
        """Return newest fake reviews by id."""
        return sorted(self._reviews, key=lambda review: review.id, reverse=True)[:count]

    def metadata(self) -> Mapping[int, Mapping[str, Any]]:
        """Return fake metadata."""
        return {1: {"labels": ["Tiny Label"]}, 2: {"labels": ["Other Label"]}}

    def affinities(self) -> Sequence[Mapping[str, Any]]:
        """Return fake affinity rows."""
        return [
            _affinity(1, ("C001", 0.9)),
            _affinity(2, ("C001", 0.3)),
        ]

    def affinities_by_review_id(self) -> Mapping[int, Mapping[str, Any]]:
        """Return fake affinity rows keyed by review id."""
        return {int(row["review_id"]): row for row in self.affinities()}

    def memberships(self) -> dict[str, dict[str, str]]:
        """Return empty fake memberships."""
        return {}

    def communities(self) -> Sequence[Mapping[str, Any]]:
        """Return fake community metadata."""
        return [{"id": "C001", "centroid": "Indie Rock"}]

    def genre_labels(self) -> Mapping[str, str]:
        """Return fake community labels."""
        return {"C001": "Indie Rock"}

    def plattenlabels(self) -> Sequence[str]:
        """Return fake record labels."""
        return ["Other Label", "Tiny Label"]

    def year_floor(self) -> int:
        """Return fake corpus lower year bound."""
        return 1999

    def year_cap(self) -> int:
        """Return fake corpus upper year bound."""
        return 2026


def _review(
    review_id: int,
    *,
    artist: str,
    album: str,
    track_title: str,
    rating: float,
) -> Review:
    """Build one fake review."""
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=artist,
        album=album,
        text=f"{artist} {album} review text",
        rating=rating,
        release_date=date(2024, 5, review_id),
        release_year=2024,
        labels=[],
        tracklist=[
            Track(number=1, title=track_title, is_highlight=True),
            Track(number=2, title=f"{track_title} Outro"),
        ],
    )


def _affinity(review_id: int, *entries: tuple[str, float]) -> dict[str, object]:
    """Build one fake res_10 affinity row."""
    return {
        "review_id": review_id,
        "communities": {
            "res_10": [
                {"id": community_id, "score": score} for community_id, score in entries
            ],
        },
    }


@pytest.fixture()
def user_db(tmp_path) -> sqlite3.Connection:
    """Return a fresh user database for API auth tests."""
    return get_connection(tmp_path / "api-users.db")


def _client(user_db: sqlite3.Connection | None = None) -> TestClient:
    """Return a test client with the fake corpus dependency."""
    app = create_app()
    provider = FakeCorpusProvider()
    app.dependency_overrides[get_corpus_provider] = lambda: provider
    if user_db is not None:
        app.dependency_overrides[get_user_db] = lambda: user_db
        app.dependency_overrides[get_optional_user_db] = lambda: user_db
    return TestClient(app)


def _profile_payload() -> dict[str, object]:
    """Return a minimal taste profile payload selecting C001."""
    return {
        "selected_communities": ["C001"],
        "community_weights_raw": {"C001": 1.0},
        "filter_settings": {"rating_min": 6, "score_min": 0.0},
    }


def _register_with_profile(
    client: TestClient,
    *,
    email: str = "alice@example.com",
    profile: dict[str, object] | None = None,
) -> str:
    """Register a test user and return the bearer token."""
    response = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "secret123",
            "profile": profile if profile is not None else _profile_payload(),
        },
    )
    assert response.status_code == 201
    return str(response.json()["access_token"])


def test_health_endpoint() -> None:
    """Health returns a tiny liveness payload."""
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "plattenradar-api"}


def test_presets_endpoint_returns_default_modes() -> None:
    """Preset endpoint exposes the configured taste presets."""
    response = _client().get("/v1/presets")

    assert response.status_code == 200
    preset_ids = [item["id"] for item in response.json()]
    assert "balanced" in preset_ids
    assert "precise" in preset_ids
    balanced = next(item for item in response.json() if item["id"] == "balanced")
    assert balanced["icon"] == "sliders-horizontal"
    assert balanced["filter_settings"]["score_min"] == 0.4


def test_taste_filter_ui_endpoint_exposes_frontend_labels() -> None:
    """Filter UI endpoint gives the frontend semantic controls."""
    response = _client().get("/v1/taste-filter-ui")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_preset_id"] == "balanced"
    assert payload["preset_display"] == "selection_cards"
    labels = [
        control["label"] for group in payload["groups"] for control in group["controls"]
    ]
    assert "Stilpassung" in labels
    assert "Liste variieren" in labels
    expert_controls = [
        control
        for group in payload["groups"]
        for control in group["controls"]
        if control["expert"]
    ]
    assert {control["id"] for control in expert_controls} == {
        "years",
        "plattenlabels",
    }


def test_archive_recommendations_endpoint_ranks_profile_matches() -> None:
    """Archive endpoint returns a paginated recommendation response."""
    response = _client().post(
        "/v1/recommendations/archive",
        json={"profile": _profile_payload(), "limit": 1, "offset": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "archive"
    assert payload["total"] == 2
    item = payload["items"][0]
    assert item["artist"] == "Alpha"
    assert item["release_date"] == "2024-05-01"
    assert item["score_display"].endswith("% Fit")
    assert item["playlist_available"] is True
    assert item["has_tracks"] is True
    assert item["matched_tags"] == [
        {"id": "C001", "label": "Indie Rock", "affinity": 0.9, "matched": True},
    ]
    assert item["explanation_signals"]["primary_matched_labels"] == [
        "Indie Rock",
    ]


def test_archive_recommendations_requires_profile_for_guest() -> None:
    """Guest requests must send a temporary taste profile."""
    response = _client().post(
        "/v1/recommendations/archive",
        json={"limit": 1, "offset": 0},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Taste profile is required for guest requests."


def test_archive_recommendations_can_use_saved_profile(
    user_db: sqlite3.Connection,
) -> None:
    """Logged-in requests may omit the profile and use the saved one."""
    client = _client(user_db)
    token = _register_with_profile(client)

    response = client.post(
        "/v1/recommendations/archive",
        json={"limit": 1, "offset": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["artist"] == "Alpha"


def test_explicit_profile_wins_over_saved_profile(
    user_db: sqlite3.Connection,
) -> None:
    """A temporary request profile does not have to match the saved profile."""
    client = _client(user_db)
    token = _register_with_profile(
        client,
        profile={
            "selected_communities": [],
            "community_weights_raw": {},
            "filter_settings": {"rating_min": 6, "score_min": 0.0},
        },
    )

    response = client.post(
        "/v1/recommendations/archive",
        json={"profile": _profile_payload(), "limit": 1, "offset": 0},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["artist"] == "Alpha"


def test_new_reviews_endpoint_returns_latest_batch() -> None:
    """Newest-review endpoint uses newest ids and the same taste profile."""
    response = _client().post(
        "/v1/recommendations/new-reviews",
        json={
            "profile": _profile_payload(),
            "limit": 2,
            "offset": 0,
            "newest_count": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "new_reviews"
    assert payload["total"] == 2
    assert {item["artist"] for item in payload["items"]} == {"Alpha", "Beta"}
    assert all(item["matched_tags"] for item in payload["items"])
    assert all("score_display" in item for item in payload["items"])


def test_playlist_export_endpoint_returns_tunemymusic_text() -> None:
    """Playlist endpoint returns a transient TuneMyMusic export payload."""
    response = _client().post(
        "/v1/playlists/export",
        json={
            "source": "new_reviews",
            "profile": _profile_payload(),
            "playlist_name": "API Playlist",
            "target_count": 2,
            "format": "txt",
            "newest_count": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "new_reviews"
    assert payload["filename"] == "API-Playlist.txt"
    assert payload["content_type"] == "text/plain"
    assert " - " in payload["content"]
    assert payload["items"]


def test_register_login_and_profile_roundtrip(user_db: sqlite3.Connection) -> None:
    """Auth endpoints store and reload one user's taste profile."""
    client = _client(user_db)
    profile = _profile_payload()

    register_response = client.post(
        "/v1/auth/register",
        json={
            "email": "Alice@Example.com",
            "password": "secret123",
            "profile": profile,
        },
    )

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["token_type"] == "bearer"
    assert registered["user"]["email"] == "alice@example.com"
    token = registered["access_token"]

    me_response = client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"

    profile_response = client.get(
        "/v1/me/taste-profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["profile"]["selected_communities"] == ["C001"]

    updated_profile = {
        **profile,
        "selected_communities": ["C001", "C002"],
        "community_weights_raw": {"C001": 1.0, "C002": 0.5},
    }
    put_response = client.put(
        "/v1/me/taste-profile",
        json=updated_profile,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert put_response.status_code == 200
    assert put_response.json()["profile"]["selected_communities"] == ["C001", "C002"]

    login_response = client.post(
        "/v1/auth/login",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "alice@example.com"


def test_me_requires_bearer_token(user_db: sqlite3.Connection) -> None:
    """Protected profile endpoints reject missing bearer tokens."""
    response = _client(user_db).get("/v1/me")

    assert response.status_code == 401
