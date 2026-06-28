"""Tests for Wikidata client helpers."""

from __future__ import annotations

import json

from tests.fixture_paths import fixture_path

from music_review.pipeline.enrichment.wikidata_client import extract_p18_filename


def test_extract_p18_filename_reads_image_claim() -> None:
    """P18 claims expose the Commons filename."""
    fixture = fixture_path("wikidata", "entity_p18.json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    entity = payload["entities"]["Q42"]

    assert extract_p18_filename(entity) == "Douglas Adams portrait cropped.jpg"
