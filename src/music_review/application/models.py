"""Pydantic models for profiles, recommendations, and playlist exports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

SortMode = Literal["deterministic", "discovery"]
RecommendationSource = Literal["archive", "new_reviews"]
PlaylistExportFormat = Literal["txt", "csv"]

_LEGACY_SORT_MODES: dict[str, SortMode] = {
    "deterministic": "deterministic",
    "discovery": "discovery",
    "Feste Reihenfolge": "deterministic",
    "Deterministisch": "deterministic",
    "Mit Zufall": "discovery",
    "Serendipity": "discovery",
}


def _clamp_float(
    value: Any,
    *,
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    """Coerce a numeric value into a bounded float."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min_value, min(max_value, parsed))


def _str_tuple(value: Any) -> tuple[str, ...]:
    """Return stable, non-empty string values."""
    if value is None:
        return ()
    if isinstance(value, set):
        return tuple(sorted(str(item).strip() for item in value if str(item).strip()))
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = str(value).strip()
    return (text,) if text else ()


class ApiModel(BaseModel):
    """Shared base model for JSON-facing application payloads."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dict using plain Python containers."""
        return self.model_dump(mode="json")


class TasteFilterSettings(ApiModel):
    """Stored filter and ranking settings for one taste profile."""

    year_min: int | None = None
    year_max: int | None = None
    rating_min: float = 6.0
    rating_max: float = 10.0
    score_min: float = 0.0
    score_max: float = 1.0
    community_spectrum_crossover: float = 0.5
    overall_weight_alpha: float = 0.5
    overall_weight_beta: float = 0.25
    overall_weight_gamma: float = 0.25
    plattenlabel_selection: tuple[str, ...] = ()
    sort_mode: SortMode = "deterministic"
    serendipity: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("plattenlabel_selection", mode="before")
    @classmethod
    def _normalize_plattenlabels(cls, value: Any) -> tuple[str, ...]:
        """Normalize label lists from stored profiles or API payloads."""
        return _str_tuple(value)

    @field_validator("sort_mode", mode="before")
    @classmethod
    def _normalize_sort_mode(cls, value: Any) -> SortMode:
        """Normalize new and legacy sort mode labels."""
        return _LEGACY_SORT_MODES.get(str(value), "deterministic")

    @field_validator("rating_min", "rating_max", mode="before")
    @classmethod
    def _normalize_rating(cls, value: Any) -> float:
        """Clamp rating values to the plattentests.de scale."""
        return _clamp_float(value, default=6.0, min_value=0.0, max_value=10.0)

    @field_validator(
        "score_min",
        "score_max",
        "community_spectrum_crossover",
        "overall_weight_alpha",
        "overall_weight_beta",
        "overall_weight_gamma",
        "serendipity",
        mode="before",
    )
    @classmethod
    def _normalize_unit_float(cls, value: Any, info: ValidationInfo) -> float:
        """Clamp score, weight, and variation values to 0..1."""
        defaults = {
            "score_min": 0.0,
            "score_max": 1.0,
            "community_spectrum_crossover": 0.5,
            "overall_weight_alpha": 0.5,
            "overall_weight_beta": 0.25,
            "overall_weight_gamma": 0.25,
            "serendipity": 0.0,
        }
        field_name = info.field_name or ""
        return _clamp_float(
            value,
            default=defaults.get(field_name, 0.0),
            min_value=0.0,
            max_value=1.0,
        )

    @model_validator(mode="after")
    def _normalize_ranges(self) -> TasteFilterSettings:
        """Ensure min/max pairs are ordered."""
        updates: dict[str, Any] = {}
        if (
            self.year_min is not None
            and self.year_max is not None
            and self.year_min > self.year_max
        ):
            updates["year_min"] = self.year_max
            updates["year_max"] = self.year_min
        if self.rating_min > self.rating_max:
            updates["rating_min"] = self.rating_max
            updates["rating_max"] = self.rating_min
        if self.score_min > self.score_max:
            updates["score_min"] = self.score_max
            updates["score_max"] = self.score_min
        if updates:
            return self.model_copy(update=updates)
        return self

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> TasteFilterSettings:
        """Build settings from a stored profile or API payload."""
        return cls.model_validate(dict(data or {}))


class TasteProfile(ApiModel):
    """A guest or saved music taste profile."""

    schema_version: int = 1
    id: str | None = None
    user_id: str | None = None
    name: str = "Standardprofil"
    is_default: bool = True
    flow_mode: str | None = None
    selected_communities: tuple[str, ...] = ()
    artist_flow_selected_communities: tuple[str, ...] = ()
    genre_flow_selected_communities: tuple[str, ...] = ()
    community_weights_raw: dict[str, float] = Field(default_factory=dict)
    filter_settings: TasteFilterSettings = Field(default_factory=TasteFilterSettings)

    @field_validator("id", "user_id", "flow_mode", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> str | None:
        """Treat blank identifiers as absent."""
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, value: Any) -> str:
        """Keep a readable profile name."""
        text = str(value or "").strip()
        return text or "Standardprofil"

    @field_validator(
        "selected_communities",
        "artist_flow_selected_communities",
        "genre_flow_selected_communities",
        mode="before",
    )
    @classmethod
    def _normalize_communities(cls, value: Any) -> tuple[str, ...]:
        """Normalize community ID collections."""
        return _str_tuple(value)

    @field_validator("community_weights_raw", mode="before")
    @classmethod
    def _normalize_weights(cls, value: Any) -> dict[str, float]:
        """Keep only numeric community weights keyed by community id."""
        if not isinstance(value, Mapping):
            return {}
        parsed: dict[str, float] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key).strip()
            if not key:
                continue
            try:
                parsed[key] = float(raw_value)
            except (TypeError, ValueError):
                continue
        return parsed

    @field_validator("filter_settings", mode="before")
    @classmethod
    def _normalize_filter_settings(cls, value: Any) -> TasteFilterSettings:
        """Accept nested dicts or existing settings objects."""
        if isinstance(value, TasteFilterSettings):
            return value
        if isinstance(value, Mapping):
            return TasteFilterSettings.from_mapping(value)
        return TasteFilterSettings()

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_profile_name(cls, data: Any) -> Any:
        """Map legacy Streamlit profile payload names into the API field."""
        if isinstance(data, Mapping) and "name" not in data and "profile_name" in data:
            copied = dict(data)
            copied["name"] = copied.get("profile_name")
            return copied
        return data

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> TasteProfile:
        """Build a profile from legacy persisted data or an API payload."""
        return cls.model_validate(dict(data))


class ExplanationSignals(ApiModel):
    """Small visual explanation hints for recommendation cards."""

    matched_community_count: int = Field(default=0, ge=0)
    primary_matched_labels: tuple[str, ...] = ()
    fit_level: Literal["low", "medium", "high"] = "medium"

    @field_validator("primary_matched_labels", mode="before")
    @classmethod
    def _normalize_labels(cls, value: Any) -> tuple[str, ...]:
        """Normalize matched label names."""
        return _str_tuple(value)

    @field_validator("fit_level", mode="before")
    @classmethod
    def _normalize_fit_level(cls, value: Any) -> str:
        """Fall back to medium for unknown fit labels."""
        return value if value in {"low", "medium", "high"} else "medium"


class Recommendation(ApiModel):
    """One ranked album recommendation for a taste profile."""

    rank: int
    review_id: int
    artist: str
    album: str
    overall_score: float
    source: RecommendationSource = "archive"
    url: str | None = None
    year: int | None = None
    rating: float | None = None
    rating_effective: float | None = None
    labels: str = ""
    text_excerpt: str = ""
    explanation_signals: ExplanationSignals = Field(default_factory=ExplanationSignals)


class RecommendationSet(ApiModel):
    """A paginated recommendation response."""

    source: RecommendationSource
    total: int = Field(ge=0)
    limit: int = Field(ge=0)
    offset: int = Field(ge=0)
    items: tuple[Recommendation, ...]
    generated_at: str | None = None


class PlaylistExportItem(ApiModel):
    """One track row in a playlist export response."""

    review_id: int
    artist: str
    album: str
    track_title: str
    source_kind: str
    score_weight: float
    raw_score: float


class PlaylistExport(ApiModel):
    """A synchronous playlist export payload."""

    source: RecommendationSource
    name: str
    format: PlaylistExportFormat
    filename: str
    content_type: str
    content: str
    items: tuple[PlaylistExportItem, ...] = ()
