from __future__ import annotations

import importlib
import logging

import pytest


def test_neueste_spotify_playlist_section_importable() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert hasattr(module, "render_neueste_spotify_playlist_section")


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
    assert "Nächste Vorschau" in text


def test_german_cooldown_hint_empty_when_allowed() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert module._german_cooldown_hint(0) == ""
