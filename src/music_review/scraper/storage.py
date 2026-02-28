# src/music_review/scraper/storage.py

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from music_review.io.jsonl import (
    append_jsonl_line,
    load_ids_from_jsonl,
    load_jsonl_as_map,
    write_jsonl,
)
from music_review.io.reviews_jsonl import review_to_raw
from music_review.scraper.models import Review


def append_review(path: Path, review: Review) -> None:
    """Append a single review as one JSON line to the given file."""
    append_jsonl_line(path, review_to_raw(review))


def load_existing_ids(path: Path) -> set[int]:
    """Return a set of all review IDs already stored in the JSONL file."""
    return load_ids_from_jsonl(path, id_key="id", log_errors=False)


def load_corpus(path: Path) -> dict[int, dict[str, Any]]:
    """Load the full corpus from a JSONL file into an ID→dict mapping."""
    return load_jsonl_as_map(path, id_key="id", log_errors=False)


def write_corpus(path: Path, reviews: Iterable[dict[str, Any]]) -> None:
    """Write the complete corpus to a JSONL file, one review per line."""
    write_jsonl(path, reviews)