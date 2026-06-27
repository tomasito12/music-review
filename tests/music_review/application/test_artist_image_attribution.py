"""Tests for artist image attribution helpers."""

from __future__ import annotations

from music_review.application.artist_image_attribution import (
    build_attribution_text,
    is_license_allowed,
)


def test_is_license_allowed_accepts_cc_by_and_cc0() -> None:
    """Common free licenses are accepted."""
    assert is_license_allowed("CC BY 2.0")
    assert is_license_allowed("CC0 1.0")
    assert is_license_allowed("Public domain")


def test_is_license_allowed_rejects_nc_licenses() -> None:
    """Non-commercial licenses are rejected."""
    assert not is_license_allowed("CC BY-NC 2.0")


def test_build_attribution_text_includes_author_and_license() -> None:
    """Attribution text names author, license, and source."""
    text = build_attribution_text(
        title="Example portrait",
        author="User:Example",
        license_name="CC BY 2.0",
        source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
    )
    assert "Example portrait" in text
    assert "User:Example" in text
    assert "CC BY 2.0" in text
