"""Preset configurations for Plattenradar taste filters."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from music_review.application.models import ApiModel, TasteFilterSettings

DEFAULT_PRESET_ID = "balanced"


class TastePreset(ApiModel):
    """A user-facing shortcut that applies concrete filter settings."""

    id: str
    label: str
    subtitle: str
    description: str
    filter_settings: TasteFilterSettings = Field(default_factory=TasteFilterSettings)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable preset definition."""
        return self.model_dump(mode="json")


TASTE_PRESETS: tuple[TastePreset, ...] = (
    TastePreset(
        id="precise",
        label="Treffsicher",
        subtitle="Nah an deinem Profil",
        description=("Strenge Stilpassung, ohne stilreine Alben unfair zu bevorzugen."),
        filter_settings=TasteFilterSettings(
            score_min=0.50,
            score_max=1.0,
            rating_min=6,
            rating_max=10,
            overall_weight_alpha=0.60,
            overall_weight_beta=0.20,
            overall_weight_gamma=0.20,
            community_spectrum_crossover=0.50,
            sort_mode="deterministic",
            serendipity=0.0,
        ),
    ),
    TastePreset(
        id="balanced",
        label="Ausgewogen",
        subtitle="Der beste Startpunkt",
        description="Gute Mischung aus Stilpassung, Wertung und Vielschichtigkeit.",
        filter_settings=TasteFilterSettings(
            score_min=0.40,
            score_max=1.0,
            rating_min=6,
            rating_max=10,
            overall_weight_alpha=0.50,
            overall_weight_beta=0.25,
            overall_weight_gamma=0.25,
            community_spectrum_crossover=0.50,
            sort_mode="deterministic",
            serendipity=0.0,
        ),
    ),
    TastePreset(
        id="exploratory",
        label="Entdeckerisch",
        subtitle="Mehr angrenzende Stile",
        description=(
            "Öffnet die Auswahl für Alben, die etwas weiter von deinem Profil "
            "entfernt liegen."
        ),
        filter_settings=TasteFilterSettings(
            score_min=0.25,
            score_max=1.0,
            rating_min=6,
            rating_max=10,
            overall_weight_alpha=0.50,
            overall_weight_beta=0.25,
            overall_weight_gamma=0.25,
            community_spectrum_crossover=0.50,
            sort_mode="deterministic",
            serendipity=0.0,
        ),
    ),
    TastePreset(
        id="critics",
        label="Kritikerlieblinge",
        subtitle="Höher bewertete Alben zuerst",
        description="Bevorzugt Alben mit starken plattentests.de-Wertungen.",
        filter_settings=TasteFilterSettings(
            score_min=0.40,
            score_max=1.0,
            rating_min=8,
            rating_max=10,
            overall_weight_alpha=0.35,
            overall_weight_beta=0.45,
            overall_weight_gamma=0.20,
            community_spectrum_crossover=0.50,
            sort_mode="deterministic",
            serendipity=0.0,
        ),
    ),
    TastePreset(
        id="multifaceted",
        label="Vielschichtig",
        subtitle="Mehrere deiner Stile zugleich",
        description=(
            "Bevorzugt Alben, die mehrere deiner gewählten Stilrichtungen berühren."
        ),
        filter_settings=TasteFilterSettings(
            score_min=0.40,
            score_max=1.0,
            rating_min=6,
            rating_max=10,
            overall_weight_alpha=0.45,
            overall_weight_beta=0.20,
            overall_weight_gamma=0.35,
            community_spectrum_crossover=0.75,
            sort_mode="deterministic",
            serendipity=0.0,
        ),
    ),
)


def list_presets() -> tuple[TastePreset, ...]:
    """Return all user-facing taste presets in display order."""
    return TASTE_PRESETS


def get_preset(preset_id: str) -> TastePreset:
    """Return one preset by id.

    Raises:
        KeyError: if the preset id is unknown.
    """
    for preset in TASTE_PRESETS:
        if preset.id == preset_id:
            return preset
    raise KeyError(preset_id)
