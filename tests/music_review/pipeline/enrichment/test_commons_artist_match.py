"""Tests for strict Commons artist-name matching."""

from __future__ import annotations

from music_review.pipeline.enrichment.commons_artist_match import (
    artist_name_in_text,
    build_commons_context_text,
    cached_commons_image_matches_artist,
    commons_image_matches_artist,
    musicbrainz_name_matches_requested,
)


def test_artist_name_in_text_matches_multi_word_names() -> None:
    """Multi-word artist names require the full phrase."""
    assert artist_name_in_text(
        "Francis of Delirium",
        "Francis of Delirium at Haldern Pop 2024",
    )
    assert artist_name_in_text(
        "The Clientele",
        "The Clientele performing live in 2011",
    )
    assert not artist_name_in_text(
        "The Clientele",
        "Comet Gain at London Popfest 12.2.12",
    )


def test_artist_name_in_text_rejects_four_tops_homonym() -> None:
    """Single-word artist names must not match longer homonyms."""
    assert not artist_name_in_text(
        "Tops",
        "Grandala du Disc The Four Tops",
    )
    assert not artist_name_in_text(
        "Tops",
        "File:The Four Tops 1966.JPG",
    )
    assert artist_name_in_text("Tops", "Tops live at Primavera Sound 2014")


def test_artist_name_in_text_rejects_shared_suffix_homonyms() -> None:
    """Multi-word artist names must not match bands that only share a suffix token."""
    assert not artist_name_in_text(
        "Temple of Angels",
        "The Black Angels at Austin Psych Fest 2013",
    )
    assert artist_name_in_text(
        "Temple of Angels",
        "Temple of Angels at Empty Bottle Chicago",
    )


def test_short_artist_names_require_filename_prefix() -> None:
    """Very short artist names must lead the Commons filename."""
    assert not commons_image_matches_artist(
        "Sue",
        "File:Nancy Wilson King Kong Photo.jpg",
    )
    assert commons_image_matches_artist(
        "Sue",
        "File:Sue live at Primavera Sound 2014.jpg",
    )


def test_commons_image_matches_artist_uses_metadata() -> None:
    """Commons metadata is included when validating a candidate file."""
    imageinfo = {
        "extmetadata": {
            "ImageDescription": {
                "value": "Comet Gain at London Popfest on 12 February 2012",
            },
        },
    }

    assert not commons_image_matches_artist(
        "The Clientele",
        "File:Comet Gain Popfest 2012.jpg",
        imageinfo,
    )
    assert commons_image_matches_artist(
        "Comet Gain",
        "File:Comet Gain Popfest 2012.jpg",
        imageinfo,
    )


def test_build_commons_context_text_includes_description() -> None:
    """Context text combines filename and Commons extmetadata."""
    context = build_commons_context_text(
        "File:Example Band.jpg",
        {
            "extmetadata": {
                "ObjectName": {"value": "Example Band portrait"},
            },
        },
    )

    assert "Example Band" in context
    assert "portrait" in context


def test_cached_commons_image_matches_artist_checks_stored_fields() -> None:
    """Cached image records can be revalidated from stored Commons metadata."""
    assert (
        cached_commons_image_matches_artist(
            "Tops",
            commons_file="The Four Tops 1966.JPG",
            title="The Four Tops",
        )
        is False
    )
    assert cached_commons_image_matches_artist(
        "Tops",
        commons_file="Tops Primavera 2014.jpg",
        title="Tops",
    )
    assert cached_commons_image_matches_artist(
        "Alpha",
        commons_file=None,
        source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
    )


def test_musicbrainz_name_matches_requested_rejects_obvious_mismatches() -> None:
    """MusicBrainz homonyms must not count as a match for the requested artist."""
    assert not musicbrainz_name_matches_requested("Sue", "Nancy Wilson")
    assert not musicbrainz_name_matches_requested(
        "Temple of Angels",
        "The Black Angels",
    )
    assert musicbrainz_name_matches_requested("The Beatles", "Beatles")
