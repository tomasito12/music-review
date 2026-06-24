"""Tests for Plattenradar taste presets."""

from __future__ import annotations

import pytest

from music_review.application.presets import (
    DEFAULT_PRESET_ID,
    get_preset,
    list_presets,
)


def test_default_preset_is_ausgewogen() -> None:
    """Ausgewogen is the starting point for new profiles."""
    preset = get_preset(DEFAULT_PRESET_ID)

    assert preset.id == "balanced"
    assert preset.label == "Ausgewogen"
    assert preset.filter_settings.score_min == 0.4
    assert preset.filter_settings.rating_min == 6
    assert preset.filter_settings.overall_weight_alpha == 0.5
    assert preset.filter_settings.overall_weight_beta == 0.25
    assert preset.filter_settings.overall_weight_gamma == 0.25


def test_presets_keep_list_variation_disabled() -> None:
    """Taste presets do not activate ranking randomness."""
    for preset in list_presets():
        assert preset.filter_settings.sort_mode == "deterministic"
        assert preset.filter_settings.serendipity == 0


def test_preset_values_match_v1_specification() -> None:
    """The configured v1 presets follow the product specification."""
    expected = {
        "precise": (0.5, 6, 0.6, 0.2, 0.2, 0.5),
        "balanced": (0.4, 6, 0.5, 0.25, 0.25, 0.5),
        "exploratory": (0.25, 6, 0.5, 0.25, 0.25, 0.5),
        "critics": (0.4, 8, 0.35, 0.45, 0.2, 0.5),
        "multifaceted": (0.4, 6, 0.45, 0.2, 0.35, 0.75),
    }

    for preset in list_presets():
        settings = preset.filter_settings
        assert (
            settings.score_min,
            settings.rating_min,
            settings.overall_weight_alpha,
            settings.overall_weight_beta,
            settings.overall_weight_gamma,
            settings.community_spectrum_crossover,
        ) == expected[preset.id]


def test_get_preset_rejects_unknown_id() -> None:
    """Unknown preset IDs fail loudly so callers cannot silently fall back."""
    with pytest.raises(KeyError):
        get_preset("missing")


def test_preset_to_dict_is_json_ready() -> None:
    """Preset payloads can be exposed by a future API endpoint."""
    payload = get_preset("multifaceted").to_dict()

    assert payload["id"] == "multifaceted"
    assert payload["label"] == "Vielschichtig"
    assert payload["filter_settings"]["community_spectrum_crossover"] == 0.75
