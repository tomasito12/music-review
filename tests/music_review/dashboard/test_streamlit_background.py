"""Tests for Streamlit dashboard background helpers."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from music_review.dashboard import streamlit_background

# Tiny valid 1x1 PNG (transparent pixel).
_MINI_PNG_B64 = "".join(
    (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA",
        "hKmMIQAAAABJRU5ErkJggg==",
    ),
)
MINI_PNG = base64.standard_b64decode(_MINI_PNG_B64)


def test_png_bytes_to_data_url_round_trips_payload() -> None:
    """A PNG data URL should round-trip the original bytes after base64 decoding."""
    data_url = streamlit_background.png_bytes_to_data_url(MINI_PNG)
    assert data_url.startswith("data:image/png;base64,")
    payload = data_url.split(",", maxsplit=1)[1]
    assert base64.standard_b64decode(payload) == MINI_PNG


def test_build_streamlit_app_background_css_includes_url_and_selector() -> None:
    """Generated CSS should target Streamlit's app shell and embed the URL."""
    css = streamlit_background.build_streamlit_app_background_css(
        "data:image/png;base64,TEST",
    )
    assert ".stApp" in css
    assert 'url("data:image/png;base64,TEST")' in css


def test_inject_streamlit_app_background_image_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing PNG should not call ``st.markdown``."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_background.st, "markdown", capture)
    missing = tmp_path / "missing.png"
    assert streamlit_background.inject_streamlit_app_background_image(missing) is False
    assert calls == []


def test_inject_streamlit_app_background_image_writes_css(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing PNG should inject CSS with a data URL payload."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_background.st, "markdown", capture)

    png_path = tmp_path / "bg.png"
    png_path.write_bytes(MINI_PNG)

    assert streamlit_background.inject_streamlit_app_background_image(png_path) is True
    assert len(calls) == 1
    (html,), kwargs = calls[0]
    assert kwargs.get("unsafe_allow_html") is True
    assert isinstance(html, str)
    assert "data:image/png;base64," in html
