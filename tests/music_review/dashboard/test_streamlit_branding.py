"""Tests for Streamlit dashboard branding helpers."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from music_review.dashboard import streamlit_branding


def test_inject_plattenradar_navigation_logo_missing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing PNG should not call ``st.logo``."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_branding.st, "logo", capture)
    missing = tmp_path / "missing.png"
    assert streamlit_branding.inject_plattenradar_navigation_logo(missing) is False
    assert calls == []


def test_ensure_plattenradar_dashboard_chrome_invokes_background_and_logo() -> None:
    """Shell chrome should refresh background, logo, and logo shell CSS."""
    with (
        patch.object(
            streamlit_branding,
            "inject_streamlit_app_background_image",
        ) as mock_bg,
        patch.object(
            streamlit_branding,
            "inject_plattenradar_navigation_logo",
        ) as mock_logo,
        patch.object(
            streamlit_branding,
            "inject_dashboard_logo_shell_css",
        ) as mock_shell,
    ):
        streamlit_branding.ensure_plattenradar_dashboard_chrome()
    mock_bg.assert_called_once_with()
    mock_logo.assert_called_once_with()
    mock_shell.assert_called_once_with()


def test_build_dashboard_logo_shell_css_targets_logo_and_height() -> None:
    """Logo shell CSS should target Streamlit's logo ``img`` nodes and max height."""
    css = streamlit_branding.build_dashboard_logo_shell_css()
    assert 'img[data-testid="stLogo"]' in css
    assert 'img[data-testid="stSidebarLogo"]' in css
    assert '[data-testid="stLogoLink"]' in css
    assert "max-height:" in css
    assert str(streamlit_branding.LOGO_SHELL_IMAGE_MAX_HEIGHT_PX) in css


def test_inject_dashboard_logo_shell_css_emits_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shell CSS should be injected via ``st.markdown``."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_branding.st, "markdown", capture)
    streamlit_branding.inject_dashboard_logo_shell_css()
    assert len(calls) == 1
    (html,), kwargs = calls[0]
    assert isinstance(html, str)
    assert "stLogo" in html
    assert kwargs.get("unsafe_allow_html") is True


def test_inject_plattenradar_navigation_logo_renders_pil_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid PNG should call ``st.logo`` with a processed ``PIL.Image``."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_branding.st, "logo", capture)

    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (0, 0, 0, 255)).save(buf, format="PNG")
    png_path = tmp_path / "logo.png"
    png_path.write_bytes(buf.getvalue())

    assert streamlit_branding.inject_plattenradar_navigation_logo(png_path) is True
    assert len(calls) == 1
    (image_arg,), kwargs = calls[0]
    assert isinstance(image_arg, Image.Image)
    assert kwargs.get("size") == "large"


def test_welcome_start_title_inner_html_text_fallback() -> None:
    """Without PNG bytes the start page should keep the text heading."""
    html = streamlit_branding.welcome_start_title_inner_html(None)
    assert "welcome-title" in html
    assert "Plattenradar" in html
    assert "data:image" not in html


def test_welcome_start_title_inner_html_embeds_logo() -> None:
    """With PNG bytes the start page should embed a data URL image."""
    raw = b"fake-png-bytes"
    html = streamlit_branding.welcome_start_title_inner_html(raw)
    assert "welcome-title-img" in html
    assert "data:image/png;base64," in html
    assert 'alt="Plattenradar"' in html


def test_read_processed_dashboard_logo_bytes_uses_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return cached processed bytes when the logo file exists."""
    buf = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 255)).save(buf, format="PNG")
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(buf.getvalue())

    monkeypatch.setattr(
        streamlit_branding,
        "dashboard_logo_png_path",
        lambda: logo_path,
    )
    out = streamlit_branding.read_processed_dashboard_logo_bytes()
    assert out is not None
    assert out.startswith(b"\x89PNG")


def test_read_processed_dashboard_logo_bytes_missing_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing logo file should yield None."""
    missing = tmp_path / "nope.png"
    monkeypatch.setattr(
        streamlit_branding,
        "dashboard_logo_png_path",
        lambda: missing,
    )
    assert streamlit_branding.read_processed_dashboard_logo_bytes() is None


def test_inject_plattenradar_navigation_logo_fallback_on_corrupt_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corrupt bytes should fall back to passing the file path to ``st.logo``."""
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(streamlit_branding.st, "logo", capture)
    png_path = tmp_path / "bad.png"
    png_path.write_bytes(b"not-a-png")

    assert streamlit_branding.inject_plattenradar_navigation_logo(png_path) is True
    assert len(calls) == 1
    (image_arg,), kwargs = calls[0]
    assert isinstance(image_arg, str)
    assert Path(image_arg).name == "bad.png"
    assert kwargs.get("size") == "large"
