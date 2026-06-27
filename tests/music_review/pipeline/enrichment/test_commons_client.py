"""Tests for Wikimedia Commons client helpers."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.enrichment.commons_client import parse_commons_image_info


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
