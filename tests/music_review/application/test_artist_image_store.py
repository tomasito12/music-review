"""Tests for artist image JSONL store."""

from __future__ import annotations

from pathlib import Path

from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.application.artist_image_store import (
    load_artist_image_index,
    upsert_artist_image,
)


def test_upsert_artist_image_replaces_existing_entry(tmp_path: Path) -> None:
    """Upsert keeps one record per artist MBID."""
    path = tmp_path / "artist_images.jsonl"
    first = ArtistImageRecord(
        artist_mbid="mbid-1",
        artist_name="Alpha",
        status="not_found",
        fetched_at=utc_now_iso(),
        reason="no_wikidata_id",
    )
    second = ArtistImageRecord(
        artist_mbid="mbid-1",
        artist_name="Alpha",
        status="ok",
        fetched_at=utc_now_iso(),
        thumbnail_url="https://example.com/thumb.jpg",
        attribution_text="credit",
    )

    upsert_artist_image(path, first)
    upsert_artist_image(path, second)

    records = load_artist_image_index(path)
    assert len(records) == 1
    assert records["mbid-1"].status == "ok"
    assert records["mbid-1"].thumbnail_url == "https://example.com/thumb.jpg"
