"""Smoke tests for core data models."""

from __future__ import annotations

from music_review.pipeline.scraper.models import Review, Track


def test_track_creation() -> None:
    track = Track(number=1, title="Song A", duration="3:42", is_highlight=True)
    assert track.number == 1
    assert track.title == "Song A"
    assert track.duration == "3:42"
    assert track.is_highlight is True


def test_review_creation() -> None:
    review = Review(
        id=42,
        url="https://example.com/42",
        artist="Radiohead",
        album="Kid A",
        text="A masterpiece of electronic experimentation.",
    )
    assert review.id == 42
    assert review.artist == "Radiohead"
    assert review.album == "Kid A"
    assert review.rating is None
    assert review.tracklist == []
    assert review.labels == []
