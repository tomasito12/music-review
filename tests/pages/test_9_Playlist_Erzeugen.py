"""Tests for the playlist suggestion hub page."""

from __future__ import annotations

import importlib
import types

import pytest

from music_review.domain.models import Review


def _hub_module() -> types.ModuleType:
    return importlib.import_module("pages.9_Playlist_Erzeugen")


def test_playlist_hub_module_importable() -> None:
    """The playlist hub must import cleanly and expose ``main``."""
    module = _hub_module()
    assert hasattr(module, "main")


def test_render_newest_tab_delegates_to_playlist_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neueste tab loads reviews and renders the shared playlist section."""
    module = _hub_module()
    sample_reviews = [
        Review(
            id=1,
            url="https://example.org/1",
            artist="A",
            album="B",
            text="t",
        ),
    ]
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(module, "load_newest_reviews_slice", lambda _n: sample_reviews)
    monkeypatch.setattr(
        module,
        "render_neueste_playlist_section",
        lambda **kwargs: calls.append(kwargs),
    )

    module._render_newest_tab()

    assert len(calls) == 1
    assert calls[0]["reviews"] == sample_reviews


def test_render_archive_tab_delegates_to_archive_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Archive tab delegates to the archive playlist section."""
    module = _hub_module()
    archive_calls: list[bool] = []

    monkeypatch.setattr(
        module,
        "render_archive_playlist_section",
        lambda: archive_calls.append(True),
    )

    module._render_archive_tab()

    assert archive_calls == [True]
