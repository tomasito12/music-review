"""Preset and filter UI configurations for Plattenradar taste settings."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from music_review.application.models import ApiModel, TasteFilterSettings

DEFAULT_PRESET_ID = "balanced"

ControlKind = Literal["range", "slider", "segmented", "multi_select"]


class TastePreset(ApiModel):
    """A user-facing shortcut that applies concrete filter settings."""

    id: str
    label: str
    subtitle: str
    description: str
    icon: str
    filter_settings: TasteFilterSettings = Field(default_factory=TasteFilterSettings)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable preset definition."""
        return self.model_dump(mode="json")


class FilterControl(ApiModel):
    """One frontend control with a human-readable label and short help."""

    id: str
    label: str
    description: str
    kind: ControlKind
    fields: tuple[str, ...]
    expert: bool = False
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    options: tuple[str, ...] = ()


class FilterGroup(ApiModel):
    """A small group of filter controls for the taste profile screen."""

    id: str
    label: str
    description: str
    controls: tuple[FilterControl, ...]


class TasteFilterUiConfig(ApiModel):
    """Frontend-facing labels, grouping, and display guidance for filters."""

    default_preset_id: str = DEFAULT_PRESET_ID
    preset_display: Literal["selection_cards"] = "selection_cards"
    preset_display_hint: str
    groups: tuple[FilterGroup, ...]


TASTE_PRESETS: tuple[TastePreset, ...] = (
    TastePreset(
        id="precise",
        label="Treffsicher",
        subtitle="Nah an deinem Profil",
        description=("Strenge Stilpassung, ohne stilreine Alben unfair zu bevorzugen."),
        icon="crosshair",
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
        icon="sliders-horizontal",
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
        icon="compass",
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
        icon="star",
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
        icon="layers",
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

TASTE_FILTER_UI = TasteFilterUiConfig(
    preset_display_hint=(
        "Presets erscheinen als mittelgroße Auswahlkarten mit Icon, Titel und "
        "kurzem Erklärungssatz. Sie setzen die darunterliegenden Regler einmalig."
    ),
    groups=(
        FilterGroup(
            id="core_fit",
            label="Passung",
            description="Grenzt ein, wie nah Alben an deinem Musikprofil liegen.",
            controls=(
                FilterControl(
                    id="style_fit",
                    label="Stilpassung",
                    description=(
                        "Legt fest, wie stark ein Album zu deinen gewählten "
                        "Stilrichtungen passen muss."
                    ),
                    kind="range",
                    fields=("score_min", "score_max"),
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                ),
                FilterControl(
                    id="rating",
                    label="plattentests.de-Wertung",
                    description=(
                        "Beschränkt Empfehlungen auf bestimmte Wertungsbereiche."
                    ),
                    kind="range",
                    fields=("rating_min", "rating_max"),
                    min_value=0.0,
                    max_value=10.0,
                    step=0.5,
                ),
            ),
        ),
        FilterGroup(
            id="discovery_balance",
            label="Gewichtung",
            description="Steuert, was beim Sortieren besonders stark zählt.",
            controls=(
                FilterControl(
                    id="overall_weights",
                    label="Schwerpunkt",
                    description=(
                        "Balanciert Stilpassung, Wertung und Vielschichtigkeit "
                        "in der Rangliste."
                    ),
                    kind="slider",
                    fields=(
                        "overall_weight_alpha",
                        "overall_weight_beta",
                        "overall_weight_gamma",
                    ),
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                ),
                FilterControl(
                    id="community_spectrum",
                    label="Fokus oder Vielschichtigkeit",
                    description=(
                        "Steuert, ob stilreine Alben oder Alben mit mehreren "
                        "passenden Stilrichtungen stärker profitieren."
                    ),
                    kind="slider",
                    fields=("community_spectrum_crossover",),
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                ),
            ),
        ),
        FilterGroup(
            id="list_behavior",
            label="Liste",
            description="Beeinflusst, ob die Rangliste stabil bleibt oder variiert.",
            controls=(
                FilterControl(
                    id="sort_mode",
                    label="Sortierung",
                    description=(
                        "Standard bleibt stabil. Listenvariation lockert nur die "
                        "Reihenfolge, nicht dein Musikprofil."
                    ),
                    kind="segmented",
                    fields=("sort_mode",),
                    options=("deterministic", "discovery"),
                ),
                FilterControl(
                    id="serendipity",
                    label="Liste variieren",
                    description=(
                        "Erhöht, wie stark passende Alben innerhalb der Rangliste "
                        "neu gemischt werden."
                    ),
                    kind="slider",
                    fields=("serendipity",),
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                ),
            ),
        ),
        FilterGroup(
            id="advanced_limits",
            label="Expertenfilter",
            description="Zusätzliche Eingrenzungen für spezielle Suchsituationen.",
            controls=(
                FilterControl(
                    id="years",
                    label="Zeitraum",
                    description=(
                        "Beschränkt Empfehlungen auf bestimmte Erscheinungsjahre."
                    ),
                    kind="range",
                    fields=("year_min", "year_max"),
                    expert=True,
                ),
                FilterControl(
                    id="plattenlabels",
                    label="Plattenlabel",
                    description=(
                        "Optionaler Filter für Nutzer, die gezielt bestimmte "
                        "Labels ein- oder ausschließen möchten."
                    ),
                    kind="multi_select",
                    fields=("plattenlabel_selection",),
                    expert=True,
                ),
            ),
        ),
    ),
)


def list_presets() -> tuple[TastePreset, ...]:
    """Return all user-facing taste presets in display order."""
    return TASTE_PRESETS


def get_filter_ui_config() -> TasteFilterUiConfig:
    """Return frontend-facing filter labels and grouping."""
    return TASTE_FILTER_UI


def get_preset(preset_id: str) -> TastePreset:
    """Return one preset by id.

    Raises:
        KeyError: if the preset id is unknown.
    """
    for preset in TASTE_PRESETS:
        if preset.id == preset_id:
            return preset
    raise KeyError(preset_id)
