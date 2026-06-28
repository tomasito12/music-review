"""Tests for MusicBrainz Wikidata relation extraction."""

from __future__ import annotations

from music_review.pipeline.enrichment.musicbrainz_client import (
    extract_wikidata_id_from_artist,
)


def test_extract_wikidata_id_from_artist_reads_url_rel() -> None:
    """Wikidata URL relations expose a Q-ID."""
    artist = {
        "relations": [
            {
                "type": "wikidata",
                "url": {
                    "resource": "https://www.wikidata.org/wiki/Q42",
                },
            }
        ]
    }

    assert extract_wikidata_id_from_artist(artist) == "Q42"
