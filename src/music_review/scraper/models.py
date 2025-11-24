# src/music_review/scraper/models.py

#from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class Track:
    """Represents a single track on an album."""

    number: int | None
    title: str
    duration: str | None = None  # e.g. "3:42"
    is_highlight: bool = False


@dataclass(slots=True)
class Review:
    """Represents a single plattentests.de review."""

    # Required core fields
    id: int
    url: str
    artist: str
    album: str
    text: str

    # Optional meta
    title: str | None = None
    author: str | None = None

    # Release info
    labels: list[str] = field(default_factory=list)
    release_date: date | None = None
    release_year: int | None = None

    # Ratings
    rating: float | None = None          # "Unsere Bewertung"
    user_rating: float | None = None     # "Eure Durchschnitts-Bewertung"

    # Content details
    tracklist: list[Track] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    total_duration: str | None = None    # e.g. "42:17"

    # Internal / scraping-related metadata (optional, but useful)
    raw_html: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
