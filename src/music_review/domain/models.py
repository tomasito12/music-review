# music_review/domain/models.py

"""Core domain models for music reviews and album metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class Track:
    """A single track on an album."""

    number: int | None
    title: str
    duration: str | None = None  # e.g. "3:42"
    is_highlight: bool = False


@dataclass(slots=True)
class Review:
    """A single album review from plattentests.de."""

    id: int
    url: str
    artist: str
    album: str
    text: str
    title: str | None = None
    author: str | None = None
    labels: list[str] = field(default_factory=list)
    release_date: date | None = None
    release_year: int | None = None
    rating: float | None = None
    user_rating: float | None = None
    tracklist: list[Track] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    total_duration: str | None = None
    references: list[str] = field(default_factory=list)
    raw_html: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
