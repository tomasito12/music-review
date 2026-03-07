# music_review/io/reviews_jsonl.py

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from music_review.domain.models import Review, Track


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _date_to_str(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _track_from_raw(raw: dict[str, Any]) -> Track:
    return Track(
        number=raw["number"],
        title=raw["title"],
        duration=raw.get("duration"),
        is_highlight=raw.get("is_highlight", False),
    )


def _track_to_raw(track: Track) -> dict[str, Any]:
    return {
        "number": track.number,
        "title": track.title,
        "duration": track.duration,
        "is_highlight": track.is_highlight,
    }


def review_from_raw(raw: dict[str, Any]) -> Review:
    """Convert a raw JSON dict into a Review instance."""
    return Review(
        id=int(raw["id"]),
        url=raw["url"],
        artist=raw["artist"],
        album=raw["album"],
        text=raw["text"],
        title=raw.get("title"),
        author=raw.get("author"),
        labels=list(raw.get("labels", [])),
        release_date=_parse_date(raw.get("release_date")),
        release_year=raw.get("release_year"),
        rating=raw.get("rating"),
        user_rating=raw.get("user_rating"),
        tracklist=[_track_from_raw(t) for t in raw.get("tracklist", [])],
        highlights=list(raw.get("highlights", [])),
        total_duration=raw.get("total_duration"),
        references=list(raw.get("references", [])),
        raw_html=raw.get("raw_html"),
        extra=dict(raw.get("extra", {})),
    )


def review_to_raw(review: Review) -> dict[str, Any]:
    """Convert a Review instance into a JSON-serialisable dict."""
    return {
        "id": review.id,
        "url": review.url,
        "artist": review.artist,
        "album": review.album,
        "text": review.text,
        "title": review.title,
        "author": review.author,
        "labels": review.labels,
        "release_date": _date_to_str(review.release_date),
        "release_year": review.release_year,
        "rating": review.rating,
        "user_rating": review.user_rating,
        "tracklist": [_track_to_raw(t) for t in review.tracklist],
        "highlights": review.highlights,
        "total_duration": review.total_duration,
        "references": review.references,
        "raw_html": review.raw_html,
        "extra": review.extra,
    }


# Alias for consumers that expect the older name.
review_to_dict = review_to_raw


def load_reviews_from_jsonl(path: str | Path) -> list[Review]:
    """Load reviews from a JSONL file into a list of Review objects."""
    file_path = Path(path)
    reviews: list[Review] = []

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            review = review_from_raw(raw)
            if not review.text.strip():
                continue
            reviews.append(review)

    return reviews


def save_reviews_to_jsonl(reviews: Iterable[Review], path: str | Path) -> None:
    """Write reviews to a JSONL file, one review per line."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        for review in reviews:
            raw = review_to_raw(review)
            line = json.dumps(raw, ensure_ascii=False)
            f.write(line + "\n")
