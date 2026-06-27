"""Tests for artist image lookup keys."""

from __future__ import annotations

from music_review.application.artist_image_lookup import (
    artist_image_lookup_key,
    is_name_lookup_key,
)


def test_artist_image_lookup_key_uses_mbid_when_present() -> None:
    """MBID-backed requests keep the MusicBrainz identifier as key."""
    assert artist_image_lookup_key("mbid-1", artist_name="Alpha") == "mbid-1"


def test_artist_image_lookup_key_uses_name_when_mbid_missing() -> None:
    """Name-only requests use a stable prefixed lookup key."""
    assert (
        artist_image_lookup_key("", artist_name="Sibylle Kefer") == "name:sibylle kefer"
    )


def test_is_name_lookup_key_detects_name_aliases() -> None:
    """Name lookup keys are recognized by their prefix."""
    assert is_name_lookup_key("name:sibylle kefer") is True
    assert is_name_lookup_key("mbid-1") is False
