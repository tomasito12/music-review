"""Tests for Commons image confidence scoring."""

from __future__ import annotations

from typing import Any

from music_review.pipeline.enrichment.commons_image_confidence import (
    ArtistContext,
    member_name_eligible_for_fallback,
    score_commons_image_candidate,
)


def _imageinfo(
    *,
    description: str = "",
    categories: str = "",
    object_name: str = "",
) -> dict[str, Any]:
    """Build a minimal Commons imageinfo payload."""
    extmetadata: dict[str, dict[str, str]] = {}
    if description:
        extmetadata["ImageDescription"] = {"value": description}
    if categories:
        extmetadata["Categories"] = {"value": categories}
    if object_name:
        extmetadata["ObjectName"] = {"value": object_name}
    return {"extmetadata": extmetadata}


def test_ortego_map_is_rejected() -> None:
    """Geography map files must not match the band name Ortego."""
    result = score_commons_image_candidate(
        "Ortego",
        "File:Ortego map.svg",
        _imageinfo(
            description="Locator map of Otago province in New Zealand",
            categories="Maps of Otago",
            object_name="Ortego map",
        ),
        context=ArtistContext(
            artist_mbid="mbid-ortego",
            resolution_source="wikidata_p18",
        ),
    )

    assert not result.accepted
    assert "excluded_content_type" in result.reasons


def test_before_the_show_seaworld_is_rejected() -> None:
    """Venue or theme-park photos must not match the band Before the Show."""
    result = score_commons_image_candidate(
        "Before the Show",
        "File:SeaWorld Before the Show.jpg",
        _imageinfo(
            description="SeaWorld show before the performance started",
            object_name="Before the Show at SeaWorld",
        ),
        context=ArtistContext(
            artist_mbid="mbid-bts",
            resolution_source="wikipedia",
        ),
    )

    assert not result.accepted
    assert (
        "venue_or_non_music_context" in result.reasons
        or "excluded_content_type" in result.reasons
    )


def test_valid_concert_photo_is_accepted() -> None:
    """Band concert photos with music context should pass MBID threshold."""
    result = score_commons_image_candidate(
        "Radiohead",
        "File:Radiohead live concert.jpg",
        _imageinfo(
            description="Radiohead performing live at a music festival",
            object_name="Radiohead live concert",
        ),
        context=ArtistContext(
            artist_mbid="mbid-radiohead",
            artist_type="Group",
            resolution_source="wikidata_p18",
        ),
    )

    assert result.accepted
    assert result.score >= 70
    assert "music_context" in result.reasons


def test_member_name_eligibility_rejects_short_names() -> None:
    """Very short member names are too ambiguous for fallback lookup."""
    assert not member_name_eligible_for_fallback("Sue")
    assert member_name_eligible_for_fallback("Thom Yorke")
