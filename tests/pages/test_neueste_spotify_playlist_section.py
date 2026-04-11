from __future__ import annotations

import importlib
import logging
import re
from datetime import UTC, datetime

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


def test_spotify_generate_button_label_unlocked() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert (
        module._german_spotify_generate_button_label(
            can_publish=True,
            seconds_remaining=999,
            now_utc=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        == "Spotify-Playlist erzeugen"
    )


def test_spotify_generate_button_label_no_suffix_when_cooldown_zero() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert (
        module._german_spotify_generate_button_label(
            can_publish=False,
            seconds_remaining=0,
            now_utc=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        == "Spotify-Playlist erzeugen"
    )


def test_spotify_generate_button_label_locked_shows_local_time_suffix() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    text = module._german_spotify_generate_button_label(
        can_publish=False,
        seconds_remaining=125,
        now_utc=datetime(2026, 6, 15, 14, 0, 0, tzinfo=UTC),
    )
    assert re.fullmatch(
        r"Spotify-Playlist erzeugen \(um \d{2}:\d{2} Uhr erneut\)$",
        text,
    ), text
