"""Playlist generation and export service for the application boundary."""

from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from music_review.application.models import (
    PlaylistExport,
    PlaylistExportFormat,
    PlaylistExportItem,
    RecommendationSource,
)
from music_review.dashboard.playlist_builder import (
    PlaylistSuggestion,
    SelectionStrategy,
    amplify_preference_weights,
    build_album_weights,
    build_playlist_suggestions,
)
from music_review.dashboard.playlist_export import (
    ExportExtension,
    format_tune_my_music_csv,
    format_tune_my_music_txt,
    suggested_export_filename,
)
from music_review.domain.models import Review

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PlaylistRequest:
    """User choices for one synchronous playlist suggestion run."""

    source: RecommendationSource
    playlist_name: str
    target_count: int
    taste_exponent: float
    selection_strategy: SelectionStrategy


@dataclass(frozen=True, slots=True)
class PlaylistResult:
    """Generated suggestions plus ready-to-download export payloads."""

    suggestions: tuple[PlaylistSuggestion, ...]
    txt_export: PlaylistExport
    csv_export: PlaylistExport


@dataclass(frozen=True, slots=True)
class PlaylistService:
    """Build playlist suggestions and TuneMyMusic exports without Streamlit."""

    logger: logging.Logger = field(default=LOGGER)

    def generate(
        self,
        *,
        reviews: Sequence[Review],
        ranked_rows: list[dict[str, object]] | None,
        request: PlaylistRequest,
        rng: random.Random,
    ) -> PlaylistResult:
        """Generate suggestions and matching TXT/CSV export payloads."""
        suggestions = self.generate_suggestions(
            reviews=reviews,
            ranked_rows=ranked_rows,
            request=request,
            rng=rng,
        )
        playlist_name = request.playlist_name.strip() or "Plattenradar"
        return PlaylistResult(
            suggestions=tuple(suggestions),
            txt_export=self.build_export(
                suggestions=suggestions,
                source=request.source,
                playlist_name=playlist_name,
                export_format="txt",
            ),
            csv_export=self.build_export(
                suggestions=suggestions,
                source=request.source,
                playlist_name=playlist_name,
                export_format="csv",
            ),
        )

    def generate_suggestions(
        self,
        *,
        reviews: Sequence[Review],
        ranked_rows: list[dict[str, object]] | None,
        request: PlaylistRequest,
        rng: random.Random,
    ) -> list[PlaylistSuggestion]:
        """Run the album-weighting and track-picking pipeline."""
        chosen_reviews, weights, raw_scores = build_album_weights(
            list(reviews),
            ranked_rows,
        )
        if not chosen_reviews:
            self.logger.info(
                "playlist_service_generate: skipped empty chosen review pool "
                "source=%s target_count=%s",
                request.source,
                request.target_count,
            )
            return []
        alloc_weights = amplify_preference_weights(
            weights,
            exponent=request.taste_exponent,
        )
        return build_playlist_suggestions(
            reviews=chosen_reviews,
            weights=alloc_weights,
            raw_scores=raw_scores,
            target_count=request.target_count,
            rng=rng,
            selection_strategy=request.selection_strategy,
        )

    def build_export(
        self,
        *,
        suggestions: Sequence[PlaylistSuggestion],
        source: RecommendationSource,
        playlist_name: str,
        export_format: PlaylistExportFormat,
    ) -> PlaylistExport:
        """Create one text or CSV export payload for generated suggestions."""
        suggestion_list = list(suggestions)
        if export_format == "csv":
            content = format_tune_my_music_csv(suggestion_list, playlist_name)
            extension: ExportExtension = ".csv"
            content_type = "text/csv"
        else:
            content = format_tune_my_music_txt(suggestion_list)
            extension = ".txt"
            content_type = "text/plain"
        return PlaylistExport(
            source=source,
            name=playlist_name.strip() or "Plattenradar",
            format=export_format,
            filename=suggested_export_filename(playlist_name, extension=extension),
            content_type=content_type,
            content=content,
            items=tuple(_export_item(item) for item in suggestion_list),
        )


def _export_item(suggestion: PlaylistSuggestion) -> PlaylistExportItem:
    """Map one dashboard suggestion to an API-facing export item."""
    return PlaylistExportItem(
        review_id=suggestion.review_id,
        artist=suggestion.artist,
        album=suggestion.album,
        track_title=suggestion.track_title,
        source_kind=suggestion.source_kind,
        score_weight=suggestion.score_weight,
        raw_score=suggestion.raw_score,
    )
