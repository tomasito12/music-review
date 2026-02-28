"""Tests for review-specific JSONL serialization."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from music_review.domain.models import Review, Track
from music_review.io.reviews_jsonl import (
    load_reviews_from_jsonl,
    review_from_raw,
    review_to_raw,
    save_reviews_to_jsonl,
)


def test_review_from_raw_minimal() -> None:
    """Minimal raw dict produces a Review with required fields only."""
    raw = {
        "id": 42,
        "url": "https://example.com/42",
        "artist": "Artist",
        "album": "Album",
        "text": "Review text.",
    }
    r = review_from_raw(raw)
    assert r.id == 42
    assert r.artist == "Artist"
    assert r.album == "Album"
    assert r.text == "Review text."
    assert r.tracklist == []
    assert r.release_date is None
    assert r.rating is None


def test_review_from_raw_with_optional_fields() -> None:
    """Optional fields (tracklist, dates, ratings) are parsed correctly."""
    raw = {
        "id": 1,
        "url": "https://example.com/1",
        "artist": "A",
        "album": "B",
        "text": "T",
        "title": "Review title",
        "release_date": "2024-06-15",
        "release_year": 2024,
        "rating": 8.5,
        "tracklist": [
            {"number": 1, "title": "Track One", "duration": "3:00", "is_highlight": True},
        ],
    }
    r = review_from_raw(raw)
    assert r.title == "Review title"
    assert r.release_date == date(2024, 6, 15)
    assert r.release_year == 2024
    assert r.rating == 8.5
    assert len(r.tracklist) == 1
    assert r.tracklist[0].title == "Track One"
    assert r.tracklist[0].is_highlight is True


def test_review_to_raw_roundtrip() -> None:
    """review_to_raw(review_from_raw(raw)) preserves data for required and common optional fields."""
    raw = {
        "id": 10,
        "url": "https://example.com/10",
        "artist": "Band",
        "album": "Record",
        "text": "Body text.",
        "title": "Optional title",
        "release_date": "2023-01-01",
        "rating": 7.0,
        "tracklist": [],
        "labels": [],
        "highlights": [],
        "references": [],
        "extra": {},
    }
    r = review_from_raw(raw)
    out = review_to_raw(r)
    assert out["id"] == 10
    assert out["artist"] == "Band"
    assert out["album"] == "Record"
    assert out["text"] == "Body text."
    assert out["release_date"] == "2023-01-01"
    assert out["rating"] == 7.0


def test_load_and_save_reviews_roundtrip(tmp_path: Path) -> None:
    """Saving reviews to JSONL and loading back yields equivalent reviews (by id and main fields)."""
    path = tmp_path / "reviews.jsonl"
    reviews = [
        Review(
            id=1,
            url="https://example.com/1",
            artist="A",
            album="B",
            text="First review.",
            tracklist=[Track(number=1, title="Song", duration=None, is_highlight=False)],
        ),
        Review(
            id=2,
            url="https://example.com/2",
            artist="C",
            album="D",
            text="Second review.",
        ),
    ]
    save_reviews_to_jsonl(reviews, path)
    loaded = load_reviews_from_jsonl(path)
    assert len(loaded) == 2
    assert loaded[0].id == 1 and loaded[0].artist == "A" and loaded[0].text == "First review."
    assert len(loaded[0].tracklist) == 1 and loaded[0].tracklist[0].title == "Song"
    assert loaded[1].id == 2 and loaded[1].artist == "C"
