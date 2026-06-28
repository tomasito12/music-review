"""Tests for Wikidata MusicBrainz reverse lookup."""

from __future__ import annotations

from music_review.pipeline.enrichment.wikidata_client import (
    _normalize_wikidata_id,
    fetch_wikidata_id_by_musicbrainz_mbid,
)


def test_normalize_wikidata_id_accepts_entity_urls() -> None:
    """Entity URLs are normalized to Q-IDs."""
    assert _normalize_wikidata_id("http://www.wikidata.org/entity/Q44190") == "Q44190"


def test_fetch_wikidata_id_by_musicbrainz_mbid_reads_sparql_bindings(
    monkeypatch,
) -> None:
    """SPARQL bindings are converted into a Wikidata Q-ID."""
    monkeypatch.setattr(
        "music_review.pipeline.enrichment.wikidata_client._run_sparql",
        lambda _query: [
            {
                "item": {
                    "value": "http://www.wikidata.org/entity/Q44190",
                },
            },
        ],
    )

    assert (
        fetch_wikidata_id_by_musicbrainz_mbid(
            "a74b1b7f-71a5-4011-9441-d0b5e4122711",
        )
        == "Q44190"
    )
