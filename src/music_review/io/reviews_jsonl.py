# music_review/io/reviews_jsonl.py

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from music_review.domain.models import Review, Track
from music_review.io.jsonl import iter_jsonl_objects
from music_review.text_encoding import repair_plattentests_text


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp used for first_seen_at."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def _date_to_str(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _datetime_to_str(value: datetime | None) -> str | None:
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


def _repair_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return repair_plattentests_text(value)


def review_from_raw(raw: dict[str, Any]) -> Review:
    """Convert a raw JSON dict into a Review instance."""
    return Review(
        id=int(raw["id"]),
        url=raw["url"],
        artist=repair_plattentests_text(raw["artist"]),
        album=repair_plattentests_text(raw["album"]),
        text=repair_plattentests_text(raw["text"]),
        title=_repair_optional_text(raw.get("title")),
        author=_repair_optional_text(raw.get("author")),
        labels=[repair_plattentests_text(label) for label in raw.get("labels", [])],
        release_date=_parse_date(raw.get("release_date")),
        release_year=raw.get("release_year"),
        rating=raw.get("rating"),
        user_rating=raw.get("user_rating"),
        tracklist=[_track_from_raw(t) for t in raw.get("tracklist", [])],
        highlights=list(raw.get("highlights", [])),
        total_duration=raw.get("total_duration"),
        references=list(raw.get("references", [])),
        raw_html=raw.get("raw_html"),
        first_seen_at=_parse_datetime(raw.get("first_seen_at")),
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
        "first_seen_at": _datetime_to_str(review.first_seen_at),
        "extra": review.extra,
    }


# Alias for consumers that expect the older name.
review_to_dict = review_to_raw


def load_reviews_from_jsonl(path: str | Path) -> list[Review]:
    """Load reviews from a JSONL file into a list of Review objects."""
    file_path = Path(path)
    reviews: list[Review] = []

    for raw in iter_jsonl_objects(file_path, log_errors=False):
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


def _json_review_id(value: object) -> int | None:
    """Parse a review ``id`` from JSON (reject bool: ``bool`` is a ``int`` subclass)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def review_line_count_and_max_id(path: str | Path) -> tuple[int, int | None]:
    """Count lines with an integer ``id`` and return the largest ``id`` seen.

    Invalid JSON lines are skipped (same as ``iter_jsonl_objects``).
    """
    file_path = Path(path)
    n = 0
    max_id: int | None = None
    for obj in iter_jsonl_objects(file_path, log_errors=False):
        rid = _json_review_id(obj.get("id"))
        if rid is None:
            continue
        n += 1
        max_id = rid if max_id is None else max(max_id, rid)
    return n, max_id


def max_review_id_in_jsonl(path: str | Path) -> int | None:
    """Return the largest integer ``id`` in the file, or None if none exist."""
    file_path = Path(path)
    max_id: int | None = None
    for obj in iter_jsonl_objects(file_path, log_errors=False):
        rid = _json_review_id(obj.get("id"))
        if rid is None:
            continue
        max_id = rid if max_id is None else max(max_id, rid)
    return max_id
