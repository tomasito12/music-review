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
from music_review.dashboard.playlist_builder import SelectionStrategy


class RecommendationRequest(ApiModel):
    """Request payload for one recommendation list."""

    profile: TasteProfile | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NewReviewsRecommendationRequest(RecommendationRequest):
    """Request payload for recommendations from the latest reviews."""

    newest_count: int = Field(default=20, ge=1, le=200)


class PlaylistExportRequest(ApiModel):
    """Request payload for synchronous playlist suggestions and export."""

    source: RecommendationSource
    profile: TasteProfile | None = None
    playlist_name: str = "Plattenradar"
    target_count: int = Field(default=30, ge=1, le=100)
    taste_exponent: float = Field(default=1.0, ge=1.0, le=5.0)
    selection_strategy: SelectionStrategy = "stratified"
    format: PlaylistExportFormat = "txt"
    newest_count: int = Field(default=20, ge=1, le=200)
    archive_limit: int = Field(default=200, ge=1, le=1000)


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
