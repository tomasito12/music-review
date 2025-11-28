# src/music_review/scraper/storage.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from music_review.scraper.models import Review, Track


def _track_to_dict(track: Track) -> dict[str, Any]:
    return {
        "number": track.number,
        "title": track.title,
        "duration": track.duration,
        "is_highlight": track.is_highlight,
    }


def _review_to_dict(review: Review) -> dict[str, Any]:
    return {
        "id": review.id,
        "url": review.url,
        "artist": review.artist,
        "album": review.album,
        "text": review.text,
        "title": review.title,
        "author": review.author,
        "labels": review.labels,
        "release_date": (
            review.release_date.isoformat() if review.release_date else None
        ),
        "release_year": review.release_year,
        "rating": review.rating,
        "user_rating": review.user_rating,
        "tracklist": [_track_to_dict(t) for t in review.tracklist],
        "highlights": review.highlights,
        "total_duration": review.total_duration,
        "references": review.references,
        "raw_html": review.raw_html,
        "extra": review.extra,
    }


def review_to_dict(review: Review) -> dict[str, Any]:
    """Public wrapper so other modules do not rely on the private helper."""
    return _review_to_dict(review)


def append_review(path: Path, review: Review) -> None:
    """Append a single review as one JSON line to the given file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_review_to_dict(review), ensure_ascii=False) + "\n")


def load_existing_ids(path: Path) -> set[int]:
    """Return a set of all review IDs already stored in the JSONL file."""
    ids: set[int] = set()
    if not path.exists():
        return ids

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            review_id = obj.get("id")
            if isinstance(review_id, int):
                ids.add(review_id)
    return ids


def load_corpus(path: Path) -> dict[int, dict[str, Any]]:
    """Load the full corpus from a JSONL file into an ID→dict mapping."""
    corpus: dict[int, dict[str, Any]] = {}
    if not path.exists():
        return corpus

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            review_id = obj.get("id")
            if not isinstance(review_id, int):
                continue
            corpus[review_id] = obj
    return corpus


def write_corpus(path: Path, reviews: Iterable[dict[str, Any]]) -> None:
    """Write the complete corpus to a JSONL file, one review per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in reviews:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")