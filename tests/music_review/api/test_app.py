"""Tests for the FastAPI v1 boundary."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from music_review.api.app import _community_example_artists, create_app
from music_review.api.dependencies import (
    get_artist_image_service,
    get_corpus_provider,
    get_optional_user_db,
    get_user_db,
)
from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.application.artist_image_service import ArtistImageService
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
        return {
            1: {"labels": ["Tiny Label"], "artist_mbid": "mbid-alpha"},
            2: {"labels": ["Other Label"], "artist_mbid": "mbid-beta"},
        }

    def artist_mbid_for_review(self, review_id: int) -> str | None:
        """Return fake artist MBIDs from metadata."""
        row = self.metadata().get(review_id)
        if row is None:
            return None
        artist_mbid = row.get("artist_mbid")
        return str(artist_mbid) if isinstance(artist_mbid, str) else None

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
        return [
            {
                "id": "C001",
                "centroid": "Indie Rock",
                "top_artists": ["Radiohead", "The National", "Arcade Fire"],
            },
        ]

    def broad_categories(self) -> tuple[list[str], dict[str, list[str]]]:
        """Return fake broad category mappings."""
        return ["Rock & Alternative"], {"C001": ["Rock & Alternative"]}

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


def _client(
    user_db: sqlite3.Connection | None = None,
    *,
    artist_image_service: object | None = None,
) -> TestClient:
    """Return a test client with the fake corpus dependency."""
    app = create_app()
    provider = FakeCorpusProvider()
    app.dependency_overrides[get_corpus_provider] = lambda: provider
    if artist_image_service is not None:
        app.dependency_overrides[get_artist_image_service] = lambda: (
            artist_image_service
        )
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


def test_taste_communities_endpoint_exposes_readable_profile_options() -> None:
    """Profile setup receives stable ids and user-facing community labels."""
    response = _client().get("/v1/taste-communities")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "C001",
            "label": "Indie Rock",
            "broad_categories": ["Rock & Alternative"],
            "example_artists": ["Radiohead", "The National", "Arcade Fire"],
        },
    ]


def test_community_example_artists_returns_up_to_three_names() -> None:
    """Example artists are trimmed and capped like the Streamlit profile cards."""
    assert _community_example_artists(
        {"top_artists": [" Radiohead ", "The National", "Arcade Fire", "Ignored"]},
        limit=3,
    ) == ("Radiohead", "The National", "Arcade Fire")
    assert _community_example_artists(
        {
            "top_artists": [
                "One",
                "Two",
                "Three",
                "Four",
                "Five",
                "Six",
                "Seven",
            ],
        },
    ) == ("One", "Two", "Three", "Four", "Five", "Six")
    assert _community_example_artists({}) == ()
    assert _community_example_artists({"top_artists": [" ", ""]}) == ()


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
    assert item["artist_mbid"] == "mbid-alpha"


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


def test_playlist_export_accepts_large_newest_count() -> None:
    """Playlist export must not fail when newest_count exceeds pagination limit."""
    response = _client().post(
        "/v1/playlists/export",
        json={
            "source": "new_reviews",
            "profile": _profile_payload(),
            "playlist_name": "Large Pool",
            "target_count": 2,
            "format": "txt",
            "newest_count": 200,
            "taste_exponent": 3.0,
            "selection_strategy": "weighted_sample",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "new_reviews"
    assert payload["items"]


def test_playlist_export_accepts_large_archive_limit() -> None:
    """Playlist export must not fail when archive_limit exceeds pagination limit."""
    response = _client().post(
        "/v1/playlists/export",
        json={
            "source": "archive",
            "profile": _profile_payload(),
            "playlist_name": "Archive Pool",
            "target_count": 2,
            "format": "txt",
            "archive_limit": 200,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "archive"
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


def _auth_token(client: TestClient, user_db: sqlite3.Connection) -> str:
    """Register one user and return a bearer token."""
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "favorites@example.com",
            "password": "secret123",
            "profile": _profile_payload(),
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_favorites_requires_bearer_token(user_db: sqlite3.Connection) -> None:
    """Favorites endpoints reject missing bearer tokens."""
    client = _client(user_db)
    assert client.get("/v1/me/favorites").status_code == 401
    assert (
        client.put(
            "/v1/me/favorites/1",
            json={
                "artist": "Alpha",
                "album": "First",
                "review_url": "https://example.com/1",
                "source": "archive",
            },
        ).status_code
        == 401
    )


def test_favorites_put_get_delete_roundtrip(user_db: sqlite3.Connection) -> None:
    """Users can save, list, and remove one favorite album."""
    client = _client(user_db)
    token = _auth_token(client, user_db)
    headers = {"Authorization": f"Bearer {token}"}

    put_response = client.put(
        "/v1/me/favorites/1",
        json={
            "artist": "Alpha",
            "album": "First",
            "review_url": "https://example.com/1",
            "source": "new_reviews",
        },
        headers=headers,
    )
    assert put_response.status_code == 200
    saved = put_response.json()
    assert saved["review_id"] == 1
    assert saved["artist"] == "Alpha"
    assert saved["source"] == "new_reviews"

    list_response = client.get("/v1/me/favorites", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["album"] == "First"

    duplicate_response = client.put(
        "/v1/me/favorites/1",
        json={
            "artist": "Changed",
            "album": "Changed",
            "review_url": "https://example.com/1",
            "source": "archive",
        },
        headers=headers,
    )
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["artist"] == "Alpha"

    delete_response = client.delete("/v1/me/favorites/1", headers=headers)
    assert delete_response.status_code == 204
    assert client.get("/v1/me/favorites", headers=headers).json()["items"] == []


def test_favorites_put_returns_404_for_unknown_review(
    user_db: sqlite3.Connection,
) -> None:
    """Saving an unknown review id returns 404."""
    client = _client(user_db)
    token = _auth_token(client, user_db)
    response = client.put(
        "/v1/me/favorites/999",
        json={
            "artist": "Ghost",
            "album": "Missing",
            "review_url": "https://example.com/999",
            "source": "archive",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_favorites_merge_skips_unknown_reviews(user_db: sqlite3.Connection) -> None:
    """Merge inserts valid rows and skips unknown review ids."""
    client = _client(user_db)
    token = _auth_token(client, user_db)
    headers = {"Authorization": f"Bearer {token}"}

    merge_response = client.post(
        "/v1/me/favorites/merge",
        json={
            "items": [
                {
                    "review_id": 1,
                    "artist": "Alpha",
                    "album": "First",
                    "review_url": "https://example.com/1",
                    "source": "archive",
                    "saved_at": "2026-01-01T10:00:00Z",
                },
                {
                    "review_id": 999,
                    "artist": "Ghost",
                    "album": "Missing",
                    "review_url": "https://example.com/999",
                    "source": "archive",
                },
            ],
        },
        headers=headers,
    )
    assert merge_response.status_code == 200
    assert merge_response.json()["merged_count"] == 1
    items = client.get("/v1/me/favorites", headers=headers).json()["items"]
    assert len(items) == 1
    assert items[0]["review_id"] == 1


class FakeArtistImageService:
    """Minimal artist image service stub for API tests."""

    def __init__(
        self,
        record: ArtistImageRecord,
        *,
        has_local_file: bool = False,
    ) -> None:
        self._record = record
        self._has_local_file = has_local_file

    def lookup_cached_only(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Return a fixed lookup result."""
        return self._mapped_record(artist_mbid, artist_name=artist_name)

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Return a fixed lookup result."""
        return self._mapped_record(artist_mbid, artist_name=artist_name)

    def _mapped_record(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_name or self._record.artist_name,
            status=self._record.status,
            fetched_at=self._record.fetched_at,
            thumbnail_url=self._record.thumbnail_url,
            license=self._record.license,
            attribution_text=self._record.attribution_text,
            source_url=self._record.source_url,
            reason=self._record.reason,
            local_path=self._record.local_path,
        )

    def lookup_batch(
        self,
        artists: list[tuple[str, str | None]],
        *,
        cached_only: bool = False,
    ) -> dict[str, ArtistImageRecord]:
        """Return fixed lookup results for a batch request."""
        from music_review.application.artist_image_lookup import artist_image_lookup_key

        return {
            artist_image_lookup_key(artist_mbid, artist_name=artist_name): (
                self.lookup_cached_only(artist_mbid, artist_name=artist_name)
            )
            for artist_mbid, artist_name in artists
            if artist_image_lookup_key(artist_mbid, artist_name=artist_name)
        }

    def local_file_exists(self, record: ArtistImageRecord) -> bool:
        """Return whether the stub exposes a local thumbnail."""
        return self._has_local_file and record.status == "ok"

    def public_thumbnail_url(self, record: ArtistImageRecord) -> str | None:
        """Return the local API thumbnail URL when available."""
        if not self.local_file_exists(record):
            return None
        return f"/v1/artists/{record.artist_mbid}/image/file"


def test_artist_image_endpoint_returns_cached_thumbnail() -> None:
    """Artist image endpoint returns licensed thumbnail metadata."""
    service = FakeArtistImageService(
        ArtistImageRecord(
            artist_mbid="mbid-alpha",
            artist_name="Alpha",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/alpha.jpg",
            license="CC BY 4.0",
            attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
            source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
            local_path="artist_images/mbid-alpha.jpg",
        ),
        has_local_file=True,
    )
    client = _client(artist_image_service=service)  # type: ignore[arg-type]

    response = client.get(
        "/v1/artists/mbid-alpha/image",
        params={"artist_name": "Alpha"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "artist_mbid": "mbid-alpha",
        "artist_name": "Alpha",
        "thumbnail_url": "/v1/artists/mbid-alpha/image/file",
        "attribution_text": "Alpha by User, CC BY 4.0 via Wikimedia Commons",
        "license": "CC BY 4.0",
        "source_url": "https://commons.wikimedia.org/wiki/File:Alpha.jpg",
    }


def test_artist_image_endpoint_returns_404_without_local_file() -> None:
    """Artist image endpoint ignores cache entries without a local JPG."""
    service = FakeArtistImageService(
        ArtistImageRecord(
            artist_mbid="mbid-alpha",
            artist_name="Alpha",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/alpha.jpg",
            license="CC BY 4.0",
            attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
            source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
        ),
        has_local_file=False,
    )
    client = _client(artist_image_service=service)  # type: ignore[arg-type]

    response = client.get("/v1/artists/mbid-alpha/image")

    assert response.status_code == 404


def test_artist_image_endpoint_returns_404_when_unavailable() -> None:
    """Artist image endpoint returns 404 when no licensed image exists."""
    service = FakeArtistImageService(
        ArtistImageRecord(
            artist_mbid="mbid-missing",
            artist_name="Missing",
            status="not_found",
            fetched_at=utc_now_iso(),
            reason="no_commons_image",
        ),
    )
    client = _client(artist_image_service=service)  # type: ignore[arg-type]

    response = client.get("/v1/artists/mbid-missing/image")

    assert response.status_code == 404
    assert response.json()["detail"] == "No licensed artist image is available."


def test_artist_image_endpoint_uses_cache_on_second_request(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second request for the same MBID reuses the JSONL cache."""
    cache_path = tmp_path / "artist_images.jsonl"
    images_dir = tmp_path / "artist_images"
    images_dir.mkdir()
    (images_dir / "mbid-alpha.jpg").write_bytes(b"fake-jpeg")
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=images_dir,
        negative_ttl_days=30,
        resolve_on_demand=True,
    )
    calls: list[str] = []

    def fake_resolve(**kwargs):
        calls.append(str(kwargs.get("artist_mbid")))
        artist_mbid = kwargs.get("artist_mbid")
        artist_name = kwargs.get("artist_name")
        return ArtistImageRecord(
            artist_mbid=str(artist_mbid),
            artist_name=artist_name or "Alpha",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/alpha.jpg",
            license="CC BY 4.0",
            attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
            source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
            local_path="artist_images/mbid-alpha.jpg",
        )

    from music_review.application.artist_image_store import upsert_artist_image

    upsert_artist_image(
        cache_path,
        ArtistImageRecord(
            artist_mbid="mbid-alpha",
            artist_name="Alpha",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/alpha.jpg",
            license="CC BY 4.0",
            attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
            source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
            local_path="artist_images/mbid-alpha.jpg",
        ),
    )

    monkeypatch.setattr(
        "music_review.application.artist_image_service.resolve_artist_image",
        fake_resolve,
    )
    client = _client(artist_image_service=service)

    first = client.get("/v1/artists/mbid-alpha/image")
    second = client.get("/v1/artists/mbid-alpha/image")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(calls) == 0


class BatchFakeArtistImageService:
    """Artist image service stub with per-MBID lookup behavior."""

    resolve_on_demand = True
    has_local_file = True

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
        force: bool = False,
        context=None,
    ) -> ArtistImageRecord:
        """Return ok only for mbid-alpha or Sibylle Kefer by name."""
        return self._lookup_record(artist_mbid, artist_name=artist_name)

    def lookup_cached_only(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Return cached-only results for batch cache mode tests."""
        return self._lookup_record(artist_mbid, artist_name=artist_name)

    def _lookup_record(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None,
    ) -> ArtistImageRecord:
        """Return ok only for mbid-alpha or Sibylle Kefer by name."""
        if artist_mbid == "mbid-alpha":
            return ArtistImageRecord(
                artist_mbid=artist_mbid,
                artist_name=artist_name or "Alpha",
                status="ok",
                fetched_at=utc_now_iso(),
                thumbnail_url="https://example.com/alpha.jpg",
                license="CC BY 4.0",
                attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
                source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
            )
        if (artist_name or "").casefold() == "sibylle kefer":
            return ArtistImageRecord(
                artist_mbid="mbid-sibylle",
                artist_name="Sibylle Kefer",
                status="ok",
                fetched_at=utc_now_iso(),
                thumbnail_url="https://example.com/sibylle.jpg",
                license="CC BY 4.0",
                attribution_text=(
                    "Sibylle Kefer by User, CC BY 4.0 via Wikimedia Commons"
                ),
                source_url="https://commons.wikimedia.org/wiki/File:Sibylle.jpg",
            )
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_name or "Missing",
            status="not_found",
            fetched_at=utc_now_iso(),
            reason="no_commons_image",
        )

    def lookup_batch(
        self,
        artists: list[tuple[str, str | None]],
        *,
        cached_only: bool = False,
    ) -> dict[str, ArtistImageRecord]:
        """Return batch lookup results."""
        from music_review.application.artist_image_lookup import artist_image_lookup_key

        results: dict[str, ArtistImageRecord] = {}
        for artist_mbid, artist_name in artists:
            lookup_key = artist_image_lookup_key(artist_mbid, artist_name=artist_name)
            if not lookup_key or lookup_key in results:
                continue
            if cached_only:
                results[lookup_key] = self.lookup_cached_only(
                    artist_mbid,
                    artist_name=artist_name,
                )
            else:
                results[lookup_key] = self.lookup(artist_mbid, artist_name=artist_name)
        return results

    def public_thumbnail_url(self, record: ArtistImageRecord) -> str | None:
        """Return the local API thumbnail URL when available."""
        if record.status != "ok" or not self.has_local_file:
            return None
        return f"/v1/artists/{record.artist_mbid}/image/file"

    def local_file_exists(self, record: ArtistImageRecord) -> bool:
        """Return whether the stub exposes a local thumbnail."""
        return self.has_local_file and record.status == "ok"


def test_artist_images_batch_endpoint_returns_available_images() -> None:
    """Batch endpoint returns one result per requested artist."""
    client = _client(artist_image_service=BatchFakeArtistImageService())  # type: ignore[arg-type]

    response = client.post(
        "/v1/artists/images",
        json={
            "artists": [
                {"artist_mbid": "mbid-alpha", "artist_name": "Alpha"},
                {"artist_mbid": "mbid-missing", "artist_name": "Missing"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["artist_mbid"] == "mbid-alpha"
    assert payload["items"][0]["image"]["artist_mbid"] == "mbid-alpha"
    assert payload["items"][0]["image"]["thumbnail_url"] == (
        "/v1/artists/mbid-alpha/image/file"
    )
    assert payload["items"][1]["artist_mbid"] == "mbid-missing"
    assert payload["items"][1]["image"] is None


def test_artist_images_batch_endpoint_skips_cache_without_local_file() -> None:
    """Batch endpoint returns null when only remote cache metadata exists."""
    service = BatchFakeArtistImageService()
    service.has_local_file = False
    client = _client(artist_image_service=service)  # type: ignore[arg-type]

    response = client.post(
        "/v1/artists/images",
        json={
            "artists": [
                {"artist_mbid": "mbid-alpha", "artist_name": "Alpha"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["image"] is None


def test_artist_images_batch_endpoint_resolves_name_only_artists() -> None:
    """Batch endpoint resolves artists without a MusicBrainz MBID by name."""
    client = _client(artist_image_service=BatchFakeArtistImageService())  # type: ignore[arg-type]

    response = client.post(
        "/v1/artists/images",
        json={
            "artists": [
                {"artist_mbid": "", "artist_name": "Sibylle Kefer"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["artist_mbid"] == "name:sibylle kefer"
    assert payload["items"][0]["image"]["artist_name"] == "Sibylle Kefer"
    assert payload["items"][0]["image"]["thumbnail_url"] == (
        "/v1/artists/mbid-sibylle/image/file"
    )


def test_artist_image_file_endpoint_returns_local_jpg(tmp_path) -> None:
    """File endpoint serves a locally cached JPG."""
    images_dir = tmp_path / "artist_images"
    images_dir.mkdir()
    image_path = images_dir / "mbid-alpha.jpg"
    image_path.write_bytes(b"fake-jpeg")
    cache_path = tmp_path / "artist_images.jsonl"
    from music_review.application.artist_image_store import upsert_artist_image

    upsert_artist_image(
        cache_path,
        ArtistImageRecord(
            artist_mbid="mbid-alpha",
            artist_name="Alpha",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/alpha.jpg",
            local_path="artist_images/mbid-alpha.jpg",
        ),
    )
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=images_dir,
        negative_ttl_days=30,
    )
    client = _client(artist_image_service=service)

    response = client.get("/v1/artists/mbid-alpha/image/file")

    assert response.status_code == 200
    assert response.content == b"fake-jpeg"
    assert response.headers["cache-control"] == "public, max-age=86400"
