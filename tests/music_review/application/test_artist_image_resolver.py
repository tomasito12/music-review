"""Tests for artist image resolver orchestration."""

from __future__ import annotations

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.application.artist_image_resolver import resolve_artist_image


def test_resolve_artist_image_returns_ok_record(monkeypatch) -> None:
    """A full successful chain yields an ok cache record."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: "Q42",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_filename",
        lambda _qid: "Example.jpg",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_image_info",
        lambda _filename: CommonsImageInfo(
            commons_file="Example.jpg",
            image_url="https://example.com/full.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            license="CC BY 2.0",
            license_url="https://creativecommons.org/licenses/by/2.0/",
            author="User:Example",
            source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
            attribution_text="credit",
            title="Example",
        ),
    )

    record = resolve_artist_image(
        artist_mbid="mbid-1",
        artist_name="Example Artist",
    )

    assert record.status == "ok"
    assert record.thumbnail_url == "https://example.com/thumb.jpg"
    assert record.wikidata_id == "Q42"


def test_resolve_artist_image_records_missing_wikidata(monkeypatch) -> None:
    """Missing Wikidata links are stored as negative cache entries."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: None,
    )

    record = resolve_artist_image(
        artist_mbid="mbid-2",
        artist_name="No Wikidata",
    )

    assert record.status == "not_found"
    assert record.reason == "no_wikidata_id"
