"""Tests for artist image batch and pipeline helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from music_review.application.artist_image_batch import (
    artist_lookup_from_review_metadata,
    fetch_missing_artist_images,
    unique_artists_from_metadata,
)
from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso


def test_unique_artists_from_metadata_deduplicates_mbids(tmp_path: Path) -> None:
    """Metadata sampling returns one row per artist MBID."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        "\n".join(
            [
                '{"review_id": 1, "artist": "Alpha", "artist_mbid": "mbid-1"}',
                '{"review_id": 2, "artist": "Alpha Dup", "artist_mbid": "mbid-1"}',
                '{"review_id": 3, "artist": "Beta", "artist_mbid": "mbid-2"}',
            ],
        ),
        encoding="utf-8",
    )

    assert unique_artists_from_metadata(metadata_path) == [
        ("mbid-1", "Alpha"),
        ("mbid-2", "Beta"),
    ]


def test_artist_lookup_from_review_metadata_returns_mbid_and_name() -> None:
    """Review metadata lookup exposes artist MBID and display name."""
    metadata = {
        10: {"artist": "Radiohead", "artist_mbid": "mbid-rh"},
        11: {"artist": "Unknown"},
    }

    assert artist_lookup_from_review_metadata(metadata, 10) == ("mbid-rh", "Radiohead")
    assert artist_lookup_from_review_metadata(metadata, 11) == (None, "Unknown")
    assert artist_lookup_from_review_metadata(metadata, 99) == (None, "")


@dataclass
class FakeArtistImageLookupService:
    """Stub service for batch fetch tests."""

    cached_mbids: set[str] = field(default_factory=set)
    lookup_calls: list[str] = field(default_factory=list)

    def cached_record(self, artist_mbid: str) -> ArtistImageRecord | None:
        """Return a cached ok record for selected MBIDs."""
        if artist_mbid not in self.cached_mbids:
            return None
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_mbid,
            status="ok",
            fetched_at=utc_now_iso(),
        )

    def is_negative_cache_fresh(self, record: ArtistImageRecord) -> bool:
        """Negative cache is never fresh in this stub."""
        return record.status == "not_found"

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Record one lookup and return an ok record."""
        self.lookup_calls.append(artist_mbid)
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_name or artist_mbid,
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/thumb.jpg",
        )


def test_fetch_missing_artist_images_respects_limit() -> None:
    """Batch fetch only resolves artists that are not already cached."""
    service = FakeArtistImageLookupService(cached_mbids={"mbid-cached"})

    resolved = fetch_missing_artist_images(
        service,
        [("mbid-cached", "Cached"), ("mbid-new", "New"), ("mbid-later", "Later")],
        limit=1,
    )

    assert resolved == 1
    assert service.lookup_calls == ["mbid-new"]
