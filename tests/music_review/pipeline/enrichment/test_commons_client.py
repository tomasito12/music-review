"""Tests for Wikimedia Commons client helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from music_review.pipeline.enrichment.commons_client import (
    find_commons_image_by_artist_name,
    parse_commons_image_info,
    score_commons_search_candidate,
)
from music_review.pipeline.enrichment.commons_image_confidence import ArtistContext


def _music_imageinfo(
    imageinfo: dict[str, object],
    *,
    artist_name: str,
) -> dict[str, object]:
    """Enrich one fixture imageinfo block with music context."""
    enriched = json.loads(json.dumps(imageinfo))
    metadata = enriched.setdefault("extmetadata", {})
    metadata["ImageDescription"] = {
        "value": f"{artist_name} rock band performing live at concert",
    }
    metadata["ObjectName"] = {"value": f"{artist_name} live concert"}
    return enriched


def test_parse_commons_image_info_builds_attribution() -> None:
    """Commons imageinfo is parsed into URLs and attribution."""
    fixture = Path("tests/fixtures/commons/imageinfo_cc_by.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    imageinfo = payload["query"]["pages"]["123"]["imageinfo"][0]

    info = parse_commons_image_info("File:Example.jpg", imageinfo)

    assert info is not None
    assert info.thumbnail_url.endswith("400px-Example.jpg")
    assert info.license == "CC BY 2.0"
    assert "User:Example" in info.attribution_text


def test_score_commons_search_candidate_prefers_matching_filenames() -> None:
    """Search scoring favors filenames that contain the artist name."""
    strong = score_commons_search_candidate(
        "File:Francis of Delirium (2024) 1.jpg",
        "Francis of Delirium",
    )
    weak = score_commons_search_candidate(
        "File:Unrelated festival crowd.jpg",
        "Francis of Delirium",
    )

    assert strong >= 10
    assert weak < 10


def test_find_commons_image_by_artist_name_returns_best_licensed_match(
    monkeypatch,
) -> None:
    """Commons search tries ranked candidates until one passes license checks."""
    fixture = Path("tests/fixtures/commons/imageinfo_cc_by.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    imageinfo = payload["query"]["pages"]["123"]["imageinfo"][0]

    def fake_search(
        artist_name: str,
        *,
        exact: bool,
        limit: int,
        thumb_width: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        if artist_name != "Francis of Delirium":
            return []
        return [
            ("File:Unrelated.jpg", imageinfo),
            (
                "File:Francis of Delirium (2024) 1.jpg",
                _music_imageinfo(imageinfo, artist_name="Francis of Delirium"),
            ),
        ]

    monkeypatch.setattr(
        "music_review.pipeline.enrichment.commons_client._search_commons_image_candidates",
        fake_search,
    )

    info = find_commons_image_by_artist_name(
        "Francis of Delirium",
        context=ArtistContext(
            artist_mbid="mbid-francis",
            resolution_source="commons_search",
        ),
    )

    assert info is not None
    assert info.commons_file == "Francis of Delirium (2024) 1.jpg"


def test_find_commons_image_by_artist_name_rejects_homonym_filename(
    monkeypatch,
) -> None:
    """Short artist names must not match longer Commons homonyms."""
    fixture = Path("tests/fixtures/commons/imageinfo_cc_by.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    imageinfo = payload["query"]["pages"]["123"]["imageinfo"][0]

    monkeypatch.setattr(
        "music_review.pipeline.enrichment.commons_client._search_commons_image_candidates",
        lambda *_args, **_kwargs: [
            ("File:The Four Tops 1966.JPG", imageinfo),
        ],
    )

    assert find_commons_image_by_artist_name("Tops") is None
