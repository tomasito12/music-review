from __future__ import annotations

import importlib
import logging

import pytest


def test_neueste_spotify_playlist_section_importable() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert hasattr(module, "render_neueste_spotify_playlist_section")


def test_spotify_taste_orientation_options_map_to_exponents() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    opts = module._SPOTIFY_TASTE_ORIENTATION_OPTIONS
    exp_map = module._SPOTIFY_TASTE_ORIENTATION_EXPONENT
    assert set(opts) == set(exp_map.keys())
    assert exp_map["gar nicht"] == 1.0
    assert exp_map["etwas"] == 1.0
    assert exp_map["mittel"] == 2.0
    assert exp_map["stark"] == 3.0


def test_log_weight_summary_marks_uniform_weights(
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    with caplog.at_level(logging.DEBUG, logger=module.__name__):
        module._log_weight_summary(
            [0.25, 0.25, 0.25, 0.25],
            review_ids=[10, 20, 30, 40],
        )
    assert "uniform=True" in caplog.text
    assert "review_ids_head=" in caplog.text


def test_log_weight_summary_marks_non_uniform_weights(
    caplog: pytest.LogCaptureFixture,
) -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    with caplog.at_level(logging.DEBUG, logger=module.__name__):
        module._log_weight_summary(
            [0.5, 0.3, 0.2],
            review_ids=[1, 2, 3],
        )
    assert "uniform=False" in caplog.text


def test_german_cooldown_hint_formats_minutes_and_seconds() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    text = module._german_cooldown_hint(125)
    assert "2 Minuten" in text
    assert "5 Sekunden" in text
    assert "Nächste Playlist-Erstellung" in text


def test_german_cooldown_hint_empty_when_allowed() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert module._german_cooldown_hint(0) == ""
