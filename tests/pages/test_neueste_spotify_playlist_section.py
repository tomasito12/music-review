from __future__ import annotations

import importlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

import pytest


def test_neueste_spotify_playlist_section_importable() -> None:
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    assert hasattr(module, "render_neueste_spotify_playlist_section")
    assert hasattr(module, "render_archive_spotify_playlist_section")


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


class _StreamlitInfoRecorder:
    """Stand-in for ``st`` that records ``st.info`` and ``st.session_state.pop``."""

    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.session_state: dict[str, Any] = {}

    def info(self, message: str) -> None:
        self.info_messages.append(message)


def test_render_archive_spotify_playlist_section_renders_callout_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without any candidates the user must see an instruction, not an exception."""
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    fake_st = _StreamlitInfoRecorder()
    monkeypatch.setattr(module, "st", fake_st)
    monkeypatch.setattr(
        module,
        "configure_spotify_playlist_logging_from_env",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "archive_playlist_candidates",
        lambda: ([], None),
    )

    controls_called: list[bool] = []

    def _fake_controls(**_: Any) -> None:
        controls_called.append(True)

    monkeypatch.setattr(
        module,
        "_render_playlist_controls_and_generate",
        _fake_controls,
    )

    module.render_archive_spotify_playlist_section()

    assert controls_called == []
    assert len(fake_st.info_messages) == 1
    assert "Musikpräferenzen" in fake_st.info_messages[0]


def test_render_archive_spotify_playlist_section_uses_archive_key_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When candidates exist, the archive section delegates with key_prefix=archive."""
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    from music_review.domain.models import Review

    review = Review(
        id=1,
        url="https://example.com/1",
        artist="A",
        album="B",
        text="t",
    )
    ranked_rows = [{"review": review, "overall_score": 0.5}]

    fake_st = _StreamlitInfoRecorder()
    monkeypatch.setattr(module, "st", fake_st)
    monkeypatch.setattr(
        module,
        "configure_spotify_playlist_logging_from_env",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "archive_playlist_candidates",
        lambda: ([review], ranked_rows),
    )

    captured: dict[str, Any] = {}

    def _fake_controls(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        module,
        "_render_playlist_controls_and_generate",
        _fake_controls,
    )

    module.render_archive_spotify_playlist_section()

    assert captured["key_prefix"] == "archive"
    assert captured["log_label"] == "archive spotify"
    assert captured["pool_size_for_log"] == 1
    assert captured["reviews"] == [review]
    # Archive mode must use weighted sampling so every qualifying album has a
    # real, score-weighted chance even when the pool dwarfs ``target_count``.
    assert captured["selection_strategy"] == "weighted_sample"
    # In archive mode every taste-orientation choice must keep ranked_rows non-None
    # so the score-weighted sampling path is used.
    resolver = captured["resolve_ranked_rows"]
    assert resolver("gar nicht") is ranked_rows
    assert resolver("stark") is ranked_rows


def test_render_neueste_spotify_playlist_section_uses_newest_key_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The newest section keeps the historical ``newest`` key prefix."""
    module = importlib.import_module("pages.neueste_spotify_playlist_section")
    from music_review.domain.models import Review

    review = Review(
        id=11,
        url="https://example.com/11",
        artist="A",
        album="B",
        text="t",
    )

    fake_st = _StreamlitInfoRecorder()
    monkeypatch.setattr(module, "st", fake_st)
    monkeypatch.setattr(
        module,
        "configure_spotify_playlist_logging_from_env",
        lambda: None,
    )

    sentinel_rows = [{"review": review, "overall_score": 0.7}]
    monkeypatch.setattr(
        module,
        "preference_rank_rows_for_reviews",
        lambda _reviews: sentinel_rows,
    )

    captured: dict[str, Any] = {}

    def _fake_controls(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        module,
        "_render_playlist_controls_and_generate",
        _fake_controls,
    )

    module.render_neueste_spotify_playlist_section(reviews=[review])

    assert captured["key_prefix"] == "newest"
    assert captured["log_label"] == "newest spotify"
    # Newest mode keeps the historical, predictable largest-remainder allocator
    # because ``target_count`` and the pool size are typically close.
    assert captured["selection_strategy"] == "stratified"
    # In newest mode the "gar nicht" choice forces the uniform fallback (None).
    resolver = captured["resolve_ranked_rows"]
    assert resolver("gar nicht") is None
    assert resolver("stark") is sentinel_rows
