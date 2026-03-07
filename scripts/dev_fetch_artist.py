#!/usr/bin/env python3
"""Manual script to test MusicBrainz artist lookup."""

from music_review.pipeline.enrichment.fetch_metadata import fetch_artist_info

if __name__ == "__main__":
    result = fetch_artist_info(name="Mammoth")
    print(result)
