# src/music_review/scraper/storage.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from music_review.scraper.models import Review, Track

# src/music_review/scraper/storage.py (weiter unten)

from datetime import date


def append_review(path: Path, review: Review) -> None:
    """Append a single review as one JSON line to the given file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_review_to_dict(review), ensure_ascii=False) + "\n")


def iter_reviews(path: Path) -> Iterable[Review]:
    """Yield reviews from a JSONL file, one by one."""
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            yield _review_from_dict(data)


def load_existing_ids(path: Path) -> set[int]:
    """Return the set of all review IDs found in the JSONL file."""
    ids: set[int] = set()
    for review in iter_reviews(path):
        ids.add(review.id)
    return ids


def replace_review(path: Path, review: Review) -> None:
    """Replace an existing review (by id) in the JSONL file with a new version.

    If the review does not yet exist, it will be appended.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    target_id = review.id
    seen = False

    if path.exists():
        with path.open("r", encoding="utf-8") as src, tmp_path.open(
                "w",
                encoding="utf-8",
        ) as dst:
            for line in src:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("id") == target_id:
                    dst.write(
                        json.dumps(
                            _review_to_dict(review),
                            ensure_ascii=False,
                        )
                        + "\n",
                    )
                    seen = True
                else:
                    dst.write(line + "\n")

    if not seen:
        # Append as new review
        with tmp_path.open("a", encoding="utf-8") as dst:
            dst.write(
                json.dumps(_review_to_dict(review), ensure_ascii=False) + "\n",
            )

    tmp_path.replace(path)


def _review_to_dict(review: Review) -> dict:
    data = {
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
        "tracklist": [
            {
                "number": t.number,
                "title": t.title,
                "duration": t.duration,
                "is_highlight": t.is_highlight,
            }
            for t in review.tracklist
        ],
        "highlights": review.highlights,
        "total_duration": review.total_duration,
        "raw_html": review.raw_html,
        "extra": review.extra,
    }
    return data


def _review_from_dict(data: dict) -> Review:
    release_date_str = data.get("release_date")
    release_date = (
        date.fromisoformat(release_date_str) if release_date_str else None
    )

    tracklist = [
        Track(
            number=t.get("number"),
            title=t["title"],
            duration=t.get("duration"),
            is_highlight=bool(t.get("is_highlight", False)),
        )
        for t in data.get("tracklist", [])
    ]

    return Review(
        id=int(data["id"]),
        url=data["url"],
        artist=data["artist"],
        album=data["album"],
        text=data["text"],
        title=data.get("title"),
        author=data.get("author"),
        labels=list(data.get("labels", [])),
        release_date=release_date,
        release_year=data.get("release_year"),
        rating=data.get("rating"),
        user_rating=data.get("user_rating"),
        tracklist=tracklist,
        highlights=list(data.get("highlights", [])),
        total_duration=data.get("total_duration"),
        raw_html=data.get("raw_html"),
        extra=data.get("extra", {}),
    )
