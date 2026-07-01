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
    assert preset.filter_settings.overall_weight_alpha == 0.7
    assert preset.filter_settings.overall_weight_beta == 0.1
    assert preset.filter_settings.overall_weight_gamma == 0.2


def test_presets_keep_list_variation_disabled() -> None:
    """Taste presets do not activate ranking randomness."""
    for preset in list_presets():
        assert preset.filter_settings.sort_mode == "deterministic"
        assert preset.filter_settings.serendipity == 0


def test_preset_values_match_v1_specification() -> None:
    """Presets share filter baselines and differ mainly in score weighting."""
    shared_filters = (0.4, 6)
    expected = {
        "precise": (*shared_filters, 0.8, 0.05, 0.1),
        "balanced": (*shared_filters, 0.7, 0.1, 0.2),
        "exploratory": (*shared_filters, 0.5, 0.25, 0.25),
        "critics": (*shared_filters, 0.6, 0.3, 0.1),
        "multifaceted": (*shared_filters, 0.5, 0.15, 0.35),
        "style_pure": (*shared_filters, 0.85, 0.15, 0.0),
    }

    for preset in list_presets():
        settings = preset.filter_settings
        assert (
            settings.score_min,
            settings.rating_min,
            settings.overall_weight_alpha,
            settings.overall_weight_beta,
            settings.overall_weight_gamma,
        ) == expected[preset.id]


def test_preset_weights_are_non_negative() -> None:
    """Each preset stores non-negative score weights."""
    for preset in list_presets():
        settings = preset.filter_settings
        assert settings.overall_weight_alpha >= 0.0
        assert settings.overall_weight_beta >= 0.0
        assert settings.overall_weight_gamma >= 0.0


def test_get_preset_rejects_unknown_id() -> None:
    """Unknown preset IDs fail loudly so callers cannot silently fall back."""
    with pytest.raises(KeyError):
        get_preset("missing")


def test_preset_to_dict_is_json_ready() -> None:
    """Preset payloads can be exposed by a future API endpoint."""
    payload = get_preset("multifaceted").to_dict()

    assert payload["id"] == "multifaceted"
    assert payload["label"] == "Vielschichtig"
    assert payload["filter_settings"]["overall_weight_gamma"] == 0.35


def test_style_pure_preset_ignores_album_breadth_weight() -> None:
    """Stilreinheit turns off the album style breadth term in overall scoring."""
    preset = get_preset("style_pure")

    assert preset.label == "Stilreinheit"
    assert preset.filter_settings.overall_weight_gamma == 0.0
