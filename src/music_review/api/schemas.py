"""Request models for the Plattenradar HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from music_review.application.models import (
    ApiModel,
    PlaylistExportFormat,
    RecommendationSource,
    TasteProfile,
)
from music_review.dashboard.playlist_builder import AlbumSpreadMode, SelectionStrategy


class RecommendationRequest(ApiModel):
    """Request payload for one recommendation list."""

    profile: TasteProfile | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NewReviewsRecommendationRequest(RecommendationRequest):
    """Request payload for recommendations from the latest reviews."""

    update_rounds: int = Field(default=1, ge=1, le=20)
    newest_count: int | None = Field(default=None, ge=1, le=200)


class PlaylistExportRequest(ApiModel):
    """Request payload for synchronous playlist suggestions and export."""

    source: RecommendationSource
    profile: TasteProfile | None = None
    playlist_name: str = "Plattenradar"
    target_count: int = Field(default=30, ge=1, le=100)
    taste_exponent: float = Field(default=1.0, ge=1.0, le=5.0)
    selection_strategy: SelectionStrategy = "stratified"
    album_spread_mode: AlbumSpreadMode = "balanced"
    format: PlaylistExportFormat = "txt"
    update_rounds: int = Field(default=1, ge=1, le=20)
    newest_count: int | None = Field(default=None, ge=1, le=200)
    archive_limit: int = Field(default=200, ge=1, le=20000)


class HealthResponse(ApiModel):
    """Small health response for local API checks."""

    status: Literal["ok"] = "ok"
    service: str = "plattenradar-api"


class AuthRegisterRequest(ApiModel):
    """Register a user with email and password."""

    email: str
    password: str = Field(min_length=6)
    profile: TasteProfile | None = None


class AuthLoginRequest(ApiModel):
    """Login with email and password."""

    email: str
    password: str = Field(min_length=1)


class AuthUser(ApiModel):
    """Authenticated user summary."""

    slug: str
    email: str | None = None


class AuthTokenResponse(ApiModel):
    """Bearer token response for the private v1 API."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: AuthUser


class TasteProfileResponse(ApiModel):
    """Stored taste profile response for the current user."""

    profile: TasteProfile | None = None


class SaveFavoriteRequest(ApiModel):
    """Snapshot metadata stored when bookmarking one album."""

    artist: str
    album: str
    review_url: str
    source: RecommendationSource | None = None


class MergeFavoriteItem(SaveFavoriteRequest):
    """One local favorite row to merge into the user account."""

    review_id: int
    saved_at: str | None = None


class MergeFavoritesRequest(ApiModel):
    """Bulk merge payload for guest favorites after login."""

    items: tuple[MergeFavoriteItem, ...] = Field(default_factory=tuple)


class MergeFavoritesResponse(ApiModel):
    """Result of merging local favorites into the account."""

    merged_count: int = Field(ge=0)


class SavedAlbumResponse(ApiModel):
    """One saved album returned by the favorites API."""

    review_id: int
    artist: str
    album: str
    review_url: str
    source: RecommendationSource | None = None
    saved_at: str


class FavoritesListResponse(ApiModel):
    """Saved albums for the current user."""

    items: tuple[SavedAlbumResponse, ...]


class ArtistImageResponse(ApiModel):
    """Licensed artist thumbnail metadata for highlight cards."""

    artist_mbid: str
    artist_name: str
    thumbnail_url: str
    attribution_text: str
    license: str
    source_url: str


class ArtistImageLookupItem(ApiModel):
    """One artist to resolve in a batch image request."""

    artist_mbid: str
    artist_name: str | None = None


class ArtistImagesBatchRequest(ApiModel):
    """Batch request for highlight artist thumbnails."""

    artists: tuple[ArtistImageLookupItem, ...] = Field(min_length=1, max_length=10)


class ArtistImageBatchResult(ApiModel):
    """One batch lookup result, with null image when unavailable."""

    artist_mbid: str
    image: ArtistImageResponse | None = None


class ArtistImagesBatchResponse(ApiModel):
    """Batch response for highlight artist thumbnails."""

    items: tuple[ArtistImageBatchResult, ...]
