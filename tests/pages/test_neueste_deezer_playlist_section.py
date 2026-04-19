"""Tests for the Deezer playlist Streamlit section (UI behaviour)."""

from __future__ import annotations

import importlib
import re
from datetime import UTC, datetime
from typing import Any

import pytest


def test_neueste_deezer_playlist_section_importable() -> None:
    """The module exposes its two public render entrypoints."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    assert hasattr(module, "render_neueste_deezer_playlist_section")
    assert hasattr(module, "render_archive_deezer_playlist_section")


def test_deezer_taste_orientation_options_map_to_exponents() -> None:
    """Each label has a numeric amplification exponent for weight scaling."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    opts = module._DEEZER_TASTE_ORIENTATION_OPTIONS
    exp_map = module._DEEZER_TASTE_ORIENTATION_EXPONENT
    assert set(opts) == set(exp_map.keys())
    assert exp_map["gar nicht"] == 1.0
    assert exp_map["etwas"] == 1.0
    assert exp_map["mittel"] == 2.0
    assert exp_map["stark"] == 3.0


def test_deezer_generate_button_label_unlocked() -> None:
    """When publishing is allowed, no time suffix is shown."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    assert (
        module._german_deezer_generate_button_label(
            can_publish=True,
            seconds_remaining=999,
            now_utc=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        == "Deezer-Playlist erzeugen"
    )


def test_deezer_generate_button_label_no_suffix_when_cooldown_zero() -> None:
    """A zero-cooldown but ``can_publish=False`` still shows the unlocked label."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    assert (
        module._german_deezer_generate_button_label(
            can_publish=False,
            seconds_remaining=0,
            now_utc=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        == "Deezer-Playlist erzeugen"
    )


def test_deezer_generate_button_label_locked_shows_local_time_suffix() -> None:
    """When rate-limited, the label includes the next allowed local time."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    text = module._german_deezer_generate_button_label(
        can_publish=False,
        seconds_remaining=125,
        now_utc=datetime(2026, 6, 15, 14, 0, 0, tzinfo=UTC),
    )
    assert re.fullmatch(
        r"Deezer-Playlist erzeugen \(um \d{2}:\d{2} Uhr erneut\)$",
        text,
    ), text


class _StreamlitInfoRecorder:
    """Stand-in for ``st`` that records ``st.info`` and ``st.session_state.pop``."""

    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.session_state: dict[str, Any] = {}

    def info(self, message: str) -> None:
        self.info_messages.append(message)


def test_render_archive_deezer_playlist_section_renders_callout_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without any candidates the user sees an instruction, not an exception."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    fake_st = _StreamlitInfoRecorder()
    monkeypatch.setattr(module, "st", fake_st)
    monkeypatch.setattr(
        module,
        "configure_spotify_playlist_logging_from_env",
        lambda: None,
    )
    monkeypatch.setattr(module, "archive_playlist_candidates", lambda: ([], None))

    controls_called: list[bool] = []

    def _fake_controls(**_: Any) -> None:
        controls_called.append(True)

    monkeypatch.setattr(
        module,
        "_render_playlist_controls_and_generate",
        _fake_controls,
    )

    module.render_archive_deezer_playlist_section()

    assert controls_called == []
    assert len(fake_st.info_messages) == 1
    assert "Musikpräferenzen" in fake_st.info_messages[0]


def test_render_archive_deezer_playlist_section_uses_archive_key_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When candidates exist, the archive section delegates with key_prefix=archive."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
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

    module.render_archive_deezer_playlist_section()

    assert captured["key_prefix"] == "archive"
    assert captured["log_label"] == "archive deezer"
    assert captured["pool_size_for_log"] == 1
    assert captured["reviews"] == [review]
    assert captured["selection_strategy"] == "weighted_sample"
    resolver = captured["resolve_ranked_rows"]
    assert resolver("gar nicht") is ranked_rows
    assert resolver("stark") is ranked_rows


def test_render_neueste_deezer_playlist_section_uses_newest_key_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The newest section keeps the ``newest`` key prefix and stratified sampling."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
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

    module.render_neueste_deezer_playlist_section(reviews=[review])

    assert captured["key_prefix"] == "newest"
    assert captured["log_label"] == "newest deezer"
    assert captured["selection_strategy"] == "stratified"
    resolver = captured["resolve_ranked_rows"]
    assert resolver("gar nicht") is None
    assert resolver("stark") is sentinel_rows


def test_render_neueste_deezer_playlist_section_no_reviews_shows_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty review list short-circuits with a German info callout."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")

    fake_st = _StreamlitInfoRecorder()
    monkeypatch.setattr(module, "st", fake_st)
    monkeypatch.setattr(
        module,
        "configure_spotify_playlist_logging_from_env",
        lambda: None,
    )

    controls_called: list[bool] = []
    monkeypatch.setattr(
        module,
        "_render_playlist_controls_and_generate",
        lambda **_: controls_called.append(True),
    )

    module.render_neueste_deezer_playlist_section(reviews=[])

    assert controls_called == []
    assert fake_st.info_messages == ["Keine Rezensionen verfügbar."]


def test_default_newest_deezer_playlist_name_uses_today() -> None:
    """The default name embeds today's date in ISO format."""
    module = importlib.import_module("pages.neueste_deezer_playlist_section")
    name = module._default_newest_deezer_playlist_name()
    assert name.startswith("Plattenradar ")
    assert re.fullmatch(r"Plattenradar \d{4}-\d{2}-\d{2}", name)
