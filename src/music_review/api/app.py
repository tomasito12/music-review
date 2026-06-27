"""FastAPI application for the Plattenradar v1 boundary."""

from __future__ import annotations

import random
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from music_review.api.dependencies import (
    CorpusProvider,
    get_artist_image_service,
    get_corpus_provider,
    get_optional_user_db,
    get_user_db,
)
from music_review.api.schemas import (
    ArtistImageBatchResult,
    ArtistImageResponse,
    ArtistImagesBatchRequest,
    ArtistImagesBatchResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUser,
    HealthResponse,
    NewReviewsRecommendationRequest,
    PlaylistExportRequest,
    RecommendationRequest,
    TasteProfileResponse,
)
from music_review.application.artist_image_lookup import artist_image_lookup_key
from music_review.application.artist_image_models import ArtistImageRecord
from music_review.application.artist_image_service import ArtistImageService
from music_review.application.community_tags import community_tags_from_entries
from music_review.application.models import (
    CommunityMatch,
    ExplanationSignals,
    PlaylistExport,
    Recommendation,
    RecommendationSet,
    RecommendationSource,
    TasteCommunity,
    TasteProfile,
)
from music_review.application.newest_reviews_service import (
    NewestReviewsInputs,
    NewestReviewsService,
)
from music_review.application.playlist_service import PlaylistRequest, PlaylistService
from music_review.application.presets import (
    TasteFilterUiConfig,
    TastePreset,
    get_filter_ui_config,
    list_presets,
)
from music_review.application.recommendation_service import (
    RecommendationInputs,
    RecommendationService,
    selected_communities_from_profile,
)
from music_review.dashboard.user_db import (
    authenticate_user_by_email,
    create_session_token,
    create_user_with_email,
    load_user_email,
    load_user_profile,
    normalize_email,
    save_user_profile,
    validate_session_token,
)
from music_review.domain.models import Review
from music_review.text_encoding import repair_plattentests_text

CORPUS_PROVIDER_DEPENDENCY = Depends(get_corpus_provider)
USER_DB_DEPENDENCY = Depends(get_user_db)
OPTIONAL_USER_DB_DEPENDENCY = Depends(get_optional_user_db)
ARTIST_IMAGE_SERVICE_DEPENDENCY = Depends(get_artist_image_service)
AUTHORIZATION_HEADER = Header(default=None)


def create_app() -> FastAPI:
    """Create the FastAPI app used by local and future frontend clients."""
    app = FastAPI(
        title="Plattenradar API",
        version="0.1.0",
        description="Private HTTP boundary for Plattenradar v1 clients.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://127.0.0.1:5174"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Return a lightweight liveness response."""
        return HealthResponse()

    @app.get("/v1/presets", response_model=tuple[TastePreset, ...])
    def presets() -> tuple[TastePreset, ...]:
        """Return the available taste filter presets."""
        return list_presets()

    @app.get("/v1/taste-filter-ui", response_model=TasteFilterUiConfig)
    def taste_filter_ui() -> TasteFilterUiConfig:
        """Return labels and grouping for the taste filter UI."""
        return get_filter_ui_config()

    @app.get("/v1/taste-communities", response_model=tuple[TasteCommunity, ...])
    def taste_communities(
        provider: CorpusProvider = CORPUS_PROVIDER_DEPENDENCY,
    ) -> tuple[TasteCommunity, ...]:
        """Return readable communities that can be selected for a taste profile."""
        labels = provider.genre_labels()
        _category_names, category_map = provider.broad_categories()
        options = {
            TasteCommunity(
                id=str(item["id"]),
                label=_community_label(
                    str(item["id"]),
                    genre_labels=labels,
                    community=item,
                ),
                broad_categories=tuple(category_map.get(str(item["id"]), ())),
                example_artists=_community_example_artists(item),
            )
            for item in provider.communities()
            if item.get("id")
        }
        return tuple(sorted(options, key=lambda option: option.label.casefold()))

    @app.get("/v1/artists/{artist_mbid}/image", response_model=ArtistImageResponse)
    def artist_image(
        artist_mbid: str,
        artist_name: str | None = Query(default=None),
        service: ArtistImageService = ARTIST_IMAGE_SERVICE_DEPENDENCY,
    ) -> ArtistImageResponse:
        """Return a licensed artist thumbnail for highlight cards."""
        record = service.lookup(artist_mbid, artist_name=artist_name)
        return _artist_image_response_or_404(service, record)

    @app.get("/v1/artists/{artist_mbid}/image/file")
    def artist_image_file(
        artist_mbid: str,
        service: ArtistImageService = ARTIST_IMAGE_SERVICE_DEPENDENCY,
    ) -> FileResponse:
        """Return a locally cached artist thumbnail JPG."""
        record = service.cached_record(artist_mbid)
        if record is None or record.status != "ok":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No local artist image file is available.",
            )
        local_path = service.resolve_local_file_path(record)
        if local_path is None or not local_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No local artist image file is available.",
            )
        return FileResponse(
            local_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.post("/v1/artists/images", response_model=ArtistImagesBatchResponse)
    def artist_images_batch(
        request: ArtistImagesBatchRequest,
        service: ArtistImageService = ARTIST_IMAGE_SERVICE_DEPENDENCY,
    ) -> ArtistImagesBatchResponse:
        """Return licensed thumbnails for multiple highlight artists in one request."""
        records = service.lookup_batch(
            [(item.artist_mbid, item.artist_name) for item in request.artists],
        )
        items = tuple(
            ArtistImageBatchResult(
                artist_mbid=lookup_key,
                image=_artist_image_response(service, records[lookup_key])
                if lookup_key in records
                else None,
            )
            for item in request.artists
            for lookup_key in (
                artist_image_lookup_key(
                    item.artist_mbid,
                    artist_name=item.artist_name,
                ),
            )
            if lookup_key
        )
        return ArtistImagesBatchResponse(items=items)

    @app.post(
        "/v1/auth/register",
        response_model=AuthTokenResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def register(
        request: AuthRegisterRequest,
        conn: sqlite3.Connection = USER_DB_DEPENDENCY,
    ) -> AuthTokenResponse:
        """Register by email/password and return a bearer token."""
        try:
            email = normalize_email(request.email)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        slug = create_user_with_email(conn, email, request.password)
        if slug is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )
        if request.profile is not None:
            save_user_profile(conn, slug, request.profile.to_dict())
        return _token_response(conn, slug)

    @app.post("/v1/auth/login", response_model=AuthTokenResponse)
    def login(
        request: AuthLoginRequest,
        conn: sqlite3.Connection = USER_DB_DEPENDENCY,
    ) -> AuthTokenResponse:
        """Login by email/password and return a bearer token."""
        slug = authenticate_user_by_email(conn, request.email, request.password)
        if slug is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        return _token_response(conn, slug)

    @app.get("/v1/me", response_model=AuthUser)
    def me(
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection = USER_DB_DEPENDENCY,
    ) -> AuthUser:
        """Return the authenticated user."""
        slug = _require_slug(conn, authorization)
        return _auth_user(conn, slug)

    @app.get("/v1/me/taste-profile", response_model=TasteProfileResponse)
    def get_my_taste_profile(
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection = USER_DB_DEPENDENCY,
    ) -> TasteProfileResponse:
        """Return the current user's stored taste profile, if present."""
        slug = _require_slug(conn, authorization)
        data = load_user_profile(conn, slug)
        if data is None:
            return TasteProfileResponse(profile=None)
        return TasteProfileResponse(profile=TasteProfile.from_mapping(data))

    @app.put("/v1/me/taste-profile", response_model=TasteProfileResponse)
    def put_my_taste_profile(
        profile: TasteProfile,
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection = USER_DB_DEPENDENCY,
    ) -> TasteProfileResponse:
        """Replace the current user's stored taste profile."""
        slug = _require_slug(conn, authorization)
        save_user_profile(conn, slug, profile.to_dict())
        return TasteProfileResponse(profile=profile)

    @app.post("/v1/recommendations/archive", response_model=RecommendationSet)
    def archive_recommendations(
        request: RecommendationRequest,
        provider: CorpusProvider = CORPUS_PROVIDER_DEPENDENCY,
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection | None = OPTIONAL_USER_DB_DEPENDENCY,
    ) -> RecommendationSet:
        """Return archive recommendations for an explicit or saved profile."""
        profile = _resolve_profile(request.profile, conn, authorization)
        rows = _archive_rows(provider, request, profile)
        return _recommendation_set(
            source="archive",
            rows=rows,
            limit=request.limit,
            offset=request.offset,
            reviews_by_id=_reviews_by_id(provider.reviews()),
            artist_mbid_for_review=provider.artist_mbid_for_review,
        )

    @app.post("/v1/recommendations/new-reviews", response_model=RecommendationSet)
    def new_review_recommendations(
        request: NewReviewsRecommendationRequest,
        provider: CorpusProvider = CORPUS_PROVIDER_DEPENDENCY,
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection | None = OPTIONAL_USER_DB_DEPENDENCY,
    ) -> RecommendationSet:
        """Return recommendations from the latest review batch."""
        profile = _resolve_profile(request.profile, conn, authorization)
        rows = _new_review_rows(provider, request, profile)
        return _recommendation_set(
            source="new_reviews",
            rows=rows,
            limit=request.limit,
            offset=request.offset,
            artist_mbid_for_review=provider.artist_mbid_for_review,
        )

    @app.post("/v1/playlists/export", response_model=PlaylistExport)
    def playlist_export(
        request: PlaylistExportRequest,
        provider: CorpusProvider = CORPUS_PROVIDER_DEPENDENCY,
        authorization: str | None = AUTHORIZATION_HEADER,
        conn: sqlite3.Connection | None = OPTIONAL_USER_DB_DEPENDENCY,
    ) -> PlaylistExport:
        """Generate a transient playlist export for TuneMyMusic."""
        profile = _resolve_profile(request.profile, conn, authorization)
        reviews, ranked_rows = _playlist_candidates(provider, request, profile)
        result = PlaylistService().generate(
            reviews=reviews,
            ranked_rows=ranked_rows,
            request=PlaylistRequest(
                source=request.source,
                playlist_name=request.playlist_name,
                target_count=request.target_count,
                taste_exponent=request.taste_exponent,
                selection_strategy=request.selection_strategy,
            ),
            rng=random.Random(),
        )
        return result.csv_export if request.format == "csv" else result.txt_export

    return app


app = create_app()


def _artist_image_response(
    service: ArtistImageService,
    record: ArtistImageRecord,
) -> ArtistImageResponse | None:
    """Map one ok record into an API response."""
    thumbnail_url = service.public_thumbnail_url(record)
    if record.status != "ok" or not thumbnail_url:
        return None
    return ArtistImageResponse(
        artist_mbid=record.artist_mbid,
        artist_name=record.artist_name,
        thumbnail_url=thumbnail_url,
        attribution_text=record.attribution_text or "",
        license=record.license or "",
        source_url=record.source_url or "",
    )


def _artist_image_response_or_404(
    service: ArtistImageService,
    record: ArtistImageRecord,
) -> ArtistImageResponse:
    """Map one ok record or raise 404."""
    response = _artist_image_response(service, record)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No licensed artist image is available.",
        )
    return response


def _archive_rows(
    provider: CorpusProvider,
    request: RecommendationRequest,
    profile: TasteProfile,
) -> list[dict[str, Any]]:
    """Compute archive recommendation rows from provider data."""
    inputs = RecommendationInputs(
        reviews=provider.reviews(),
        metadata=provider.metadata(),
        affinities=provider.affinities(),
        memberships=provider.memberships(),
        communities=provider.communities(),
        genre_labels=provider.genre_labels(),
        plattenlabels=provider.plattenlabels(),
        year_floor=provider.year_floor(),
        year_cap=provider.year_cap(),
    )
    return RecommendationService(inputs).compute_archive_recommendations(
        profile,
    )


def _new_review_rows(
    provider: CorpusProvider,
    request: NewReviewsRecommendationRequest,
    profile: TasteProfile,
) -> list[dict[str, Any]]:
    """Compute newest-review rows from provider data."""
    newest = provider.newest_reviews(request.newest_count)
    affinity_by_id = provider.affinities_by_review_id()
    genre_labels = provider.genre_labels()
    comm_by_id = {
        str(item.get("id")): item for item in provider.communities() if item.get("id")
    }
    inputs = NewestReviewsInputs(
        newest_reviews=newest,
        affinity_by_review_id=affinity_by_id,
        memberships=provider.memberships(),
        all_reviews_for_breadth_norm=provider.reviews(),
    )
    rows = NewestReviewsService(inputs).compute_ranked_rows(profile)
    if rows is None:
        rows = [_unranked_new_review_row(review) for review in newest]
    selected_comms = selected_communities_from_profile(profile)
    return [
        _with_new_review_card_fields(
            row,
            affinity_by_review_id=affinity_by_id,
            genre_labels=genre_labels,
            comm_by_id=comm_by_id,
            selected_community_ids=selected_comms,
        )
        for row in rows
    ]


def _playlist_candidates(
    provider: CorpusProvider,
    request: PlaylistExportRequest,
    profile: TasteProfile,
) -> tuple[list[Review], list[dict[str, object]] | None]:
    """Return reviews and optional ranking rows for playlist generation."""
    if request.source == "new_reviews":
        # Recommendation request ``limit`` is only for pagination; the playlist
        # pool size comes from ``newest_count``. Keep ``limit`` within schema bounds.
        new_request = NewReviewsRecommendationRequest(
            profile=profile,
            limit=min(request.newest_count, 100),
            offset=0,
            newest_count=request.newest_count,
        )
        rows = _new_review_rows(provider, new_request, profile)
        return _reviews_from_rows(rows), _ranked_playlist_rows(rows)

    archive_request = RecommendationRequest(
        profile=profile,
        limit=min(request.archive_limit, 100),
        offset=0,
    )
    rows = _archive_rows(provider, archive_request, profile)[: request.archive_limit]
    reviews = _reviews_from_archive_rows(provider.reviews(), rows)
    ranked_rows = [
        {"review": review, "overall_score": float(row.get("overall_score", 0.0))}
        for review, row in zip(reviews, rows, strict=False)
    ]
    return reviews, ranked_rows or None


def _recommendation_set(
    *,
    source: RecommendationSource,
    rows: Sequence[Mapping[str, Any]],
    limit: int,
    offset: int,
    reviews_by_id: Mapping[int, Review] | None = None,
    artist_mbid_for_review: Callable[[int], str | None] | None = None,
) -> RecommendationSet:
    """Map raw service rows into a paginated recommendation response."""
    total = len(rows)
    page_rows = list(rows[offset : offset + limit])
    return RecommendationSet(
        source=source,
        total=total,
        limit=limit,
        offset=offset,
        generated_at=datetime.now(UTC).isoformat(),
        items=tuple(
            _recommendation_from_row(
                index + offset + 1,
                row,
                source=source,
                fallback_review=_fallback_review(row, reviews_by_id),
                artist_mbid=_artist_mbid_for_row(
                    row,
                    artist_mbid_for_review=artist_mbid_for_review,
                ),
            )
            for index, row in enumerate(page_rows)
        ),
    )


def _recommendation_from_row(
    rank: int,
    row: Mapping[str, Any],
    *,
    source: RecommendationSource,
    fallback_review: Review | None = None,
    artist_mbid: str | None = None,
) -> Recommendation:
    """Map one raw row into an API recommendation item."""
    review = row.get("review")
    if not isinstance(review, Review):
        review = fallback_review
    url: str | None
    year: int | None
    rating: float | None
    release_date: str | None
    has_tracks = False
    if isinstance(review, Review):
        artist = review.artist
        album = review.album
        url = review.url
        year = review.release_year
        release_date = review.release_date.isoformat() if review.release_date else None
        rating = review.rating
        text = review.text
        review_id = int(review.id)
        has_tracks = bool(review.tracklist)
    else:
        artist = str(row.get("artist", ""))
        album = str(row.get("album", ""))
        url = _optional_str(row.get("url"))
        year = _optional_int(row.get("year"))
        release_date = _optional_str(row.get("release_date"))
        rating = _optional_float(row.get("rating"))
        text = repair_plattentests_text(str(row.get("text", "")))
        review_id = int(row.get("review_id", 0))
    overall = float(row.get("overall_score", 0.0))
    return Recommendation(
        rank=rank,
        review_id=review_id,
        artist=artist,
        album=album,
        overall_score=overall,
        source=source,
        url=url,
        year=year,
        release_date=release_date,
        rating=rating,
        rating_effective=_optional_float(row.get("rating_effective")),
        labels=str(row.get("labels", "")),
        text_excerpt=text[:300],
        score_display=_score_display(overall),
        playlist_available=has_tracks,
        has_tracks=has_tracks,
        matched_tags=_matched_tags(row),
        explanation_signals=_explanation_signals(row),
        artist_mbid=artist_mbid,
    )


def _explanation_signals(row: Mapping[str, Any]) -> ExplanationSignals:
    """Build subtle fit hints from available row data."""
    top = row.get("top_communities")
    labels: list[str] = []
    if isinstance(top, list):
        for item in top[:3]:
            if isinstance(item, Mapping) and item.get("label"):
                labels.append(str(item["label"]))
    score = float(row.get("overall_score", row.get("score", 0.0)) or 0.0)
    fit_level: Literal["low", "medium", "high"]
    if score >= 0.75:
        fit_level = "high"
    elif score < 0.35:
        fit_level = "low"
    else:
        fit_level = "medium"
    return ExplanationSignals(
        matched_community_count=len(labels),
        primary_matched_labels=tuple(labels),
        fit_level=fit_level,
    )


def _matched_tags(row: Mapping[str, Any]) -> tuple[CommunityMatch, ...]:
    """Return frontend-ready style tags for a recommendation card."""
    top = row.get("top_communities")
    if not isinstance(top, list):
        return ()
    tags: list[CommunityMatch] = []
    for item in top:
        if not isinstance(item, Mapping):
            continue
        community_id = _optional_str(item.get("id"))
        label = _optional_str(item.get("label"))
        if not community_id or not label:
            continue
        affinity = max(
            0.0,
            float(item.get("affinity", item.get("score", 0.0)) or 0.0),
        )
        tags.append(
            CommunityMatch(
                id=community_id,
                label=label,
                affinity=affinity,
                matched=bool(item.get("matched", False)),
            ),
        )
    return tuple(tags)


def _score_display(overall_score: float) -> str:
    """Return a compact user-facing score label for recommendation cards."""
    return f"{max(0.0, min(1.0, overall_score)) * 100:.0f}% Fit"


def _token_response(conn: sqlite3.Connection, slug: str) -> AuthTokenResponse:
    """Create a bearer token response for a user slug."""
    token = create_session_token(conn, slug)
    return AuthTokenResponse(
        access_token=token,
        user=_auth_user(conn, slug),
    )


def _auth_user(conn: sqlite3.Connection, slug: str) -> AuthUser:
    """Return a public user summary."""
    return AuthUser(slug=slug, email=load_user_email(conn, slug))


def _resolve_profile(
    profile: TasteProfile | None,
    conn: sqlite3.Connection | None,
    authorization: str | None,
) -> TasteProfile:
    """Return the explicit profile or the current user's saved profile."""
    if profile is not None:
        return profile
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Taste profile is required for guest requests.",
        )
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token.",
        )
    slug = _require_slug(conn, authorization)
    data = load_user_profile(conn, slug)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No taste profile is stored for this user.",
        )
    return TasteProfile.from_mapping(data)


def _require_slug(conn: sqlite3.Connection, authorization: str | None) -> str:
    """Resolve the current user slug from an Authorization header."""
    if not authorization or not authorization.casefold().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    slug = validate_session_token(conn, token)
    if slug is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token.",
        )
    return slug


def _unranked_new_review_row(review: Review) -> dict[str, Any]:
    """Fallback row when no taste profile exists for newest reviews."""
    return {
        "review": review,
        "review_id": int(review.id),
        "overall_score": 0.0,
        "score": 0.0,
    }


def _with_new_review_card_fields(
    row: Mapping[str, Any],
    *,
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    genre_labels: Mapping[str, str],
    comm_by_id: Mapping[str, Mapping[str, Any]],
    selected_community_ids: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """Add card-facing fields that newest ranking rows do not own."""
    copied = dict(row)
    review_id = _optional_int(copied.get("review_id"))
    review = copied.get("review")
    if review_id is None and isinstance(review, Review):
        review_id = int(review.id)
    if review_id is None:
        return copied
    copied["top_communities"] = _top_communities_from_affinity(
        affinity_by_review_id.get(review_id),
        genre_labels=genre_labels,
        comm_by_id=comm_by_id,
        selected_community_ids=selected_community_ids,
    )
    return copied


def _top_communities_from_affinity(
    affinity: Mapping[str, Any] | None,
    *,
    genre_labels: Mapping[str, str],
    comm_by_id: Mapping[str, Mapping[str, Any]],
    selected_community_ids: set[str] | frozenset[str] | None = None,
) -> list[dict[str, object]]:
    """Return affinity tags in the same shape as archive rows."""
    return community_tags_from_entries(
        _affinity_entries(affinity),
        label_for_id=lambda community_id: _community_label(
            community_id,
            genre_labels=genre_labels,
            community=comm_by_id.get(community_id),
        ),
        selected_community_ids=selected_community_ids,
    )


def _affinity_entries(
    affinity: Mapping[str, Any] | None,
) -> list[Mapping[str, object]]:
    """Extract ranked community affinity entries for one review."""
    if affinity is None:
        return []
    communities = affinity.get("communities")
    if not isinstance(communities, Mapping):
        return []
    entries = communities.get("res_10")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, Mapping)]


def _community_label(
    community_id: str,
    *,
    genre_labels: Mapping[str, str],
    community: Mapping[str, Any] | None,
) -> str:
    """Return a readable community label for API cards."""
    label = genre_labels.get(community_id)
    if label:
        return label
    if community is not None and community.get("centroid"):
        return str(community["centroid"])
    return "Stil-Cluster"


def _community_example_artists(
    community: Mapping[str, Any],
    *,
    limit: int = 6,
) -> tuple[str, ...]:
    """Return up to six example artists for compact profile detail captions."""
    top = community.get("top_artists")
    if not isinstance(top, list):
        return ()
    names: list[str] = []
    for raw in top:
        text = str(raw).strip()
        if not text:
            continue
        names.append(text)
        if len(names) >= limit:
            break
    return tuple(names)


def _reviews_from_archive_rows(
    reviews: Sequence[Review],
    rows: Sequence[Mapping[str, Any]],
) -> list[Review]:
    """Resolve archive rows back to review objects for playlist generation."""
    review_by_id = {int(review.id): review for review in reviews}
    resolved: list[Review] = []
    for row in rows:
        review_id = _optional_int(row.get("review_id"))
        if review_id is None:
            continue
        review = review_by_id.get(review_id)
        if review is not None:
            resolved.append(review)
    return resolved


def _reviews_by_id(reviews: Sequence[Review]) -> dict[int, Review]:
    """Return reviews keyed by integer review id."""
    return {int(review.id): review for review in reviews}


def _artist_mbid_for_row(
    row: Mapping[str, Any],
    *,
    artist_mbid_for_review: Callable[[int], str | None] | None,
) -> str | None:
    """Resolve artist MBID for one recommendation row."""
    if artist_mbid_for_review is None:
        return None
    review_id = _optional_int(row.get("review_id"))
    if review_id is None:
        review = row.get("review")
        if isinstance(review, Review):
            review_id = int(review.id)
    if review_id is None:
        return None
    return artist_mbid_for_review(review_id)


def _fallback_review(
    row: Mapping[str, Any],
    reviews_by_id: Mapping[int, Review] | None,
) -> Review | None:
    """Resolve a fallback review object for rows that only contain review_id."""
    if reviews_by_id is None:
        return None
    review_id = _optional_int(row.get("review_id"))
    if review_id is None:
        return None
    return reviews_by_id.get(review_id)


def _reviews_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[Review]:
    """Extract review objects from newest-review rows."""
    reviews: list[Review] = []
    for row in rows:
        review = row.get("review")
        if isinstance(review, Review):
            reviews.append(review)
    return reviews


def _ranked_playlist_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, object]] | None:
    """Return rows in the shape expected by PlaylistService."""
    ranked: list[dict[str, object]] = []
    for row in rows:
        review = row.get("review")
        if not isinstance(review, Review):
            continue
        ranked.append(
            {
                "review": review,
                "overall_score": float(row.get("overall_score", 0.0)),
            },
        )
    return ranked or None


def _optional_str(value: Any) -> str | None:
    """Return a string or None for absent values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    """Return an int or None for invalid values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    """Return a float or None for invalid values."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
