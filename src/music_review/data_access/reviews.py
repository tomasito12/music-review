"""Review corpus loading and derived scans over reviews JSONL."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from music_review.data_access.paths import reviews_path
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

# When reviews.jsonl is missing or has no years: lower bound for year sliders.
YEAR_SLIDER_FALLBACK_FLOOR = 1990

# Plattenlabels with more than this many albums appear individually in filter UI.
PLATTENLABEL_INDIVIDUAL_LIST_MIN_ALBUMS = 50


def load_reviews(path: str | Path | None = None) -> list[Review]:
    """Load typed reviews from JSONL, skipping rows with empty text."""
    p = Path(path) if path is not None else reviews_path()
    if not p.is_file():
        return []
    return load_reviews_from_jsonl(p)


def review_raw_release_year(raw: Mapping[str, Any]) -> int | None:
    """Best release year from one reviews.jsonl row (year field or ISO date)."""
    ry = raw.get("release_year")
    if ry is not None:
        try:
            y = int(ry)
        except (TypeError, ValueError):
            pass
        else:
            if 1800 <= y <= 2100:
                return y
    rd = raw.get("release_date")
    if isinstance(rd, str) and len(rd) >= 4:
        try:
            y = int(rd[:4])
        except ValueError:
            return None
        if 1800 <= y <= 2100:
            return y
    return None


def max_release_year_in_jsonl(path: Path) -> int | None:
    """Scan a reviews JSONL file for the largest release year found."""
    if not path.exists():
        return None
    y_max: int | None = None
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        y = review_raw_release_year(obj)
        if y is None:
            continue
        if y_max is None or y > y_max:
            y_max = y
    return y_max


def min_release_year_in_jsonl(path: Path) -> int | None:
    """Scan a reviews JSONL file for the smallest release year found."""
    if not path.exists():
        return None
    y_min: int | None = None
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        y = review_raw_release_year(obj)
        if y is None:
            continue
        if y_min is None or y < y_min:
            y_min = y
    return y_min


def unique_plattenlabels_from_reviews_jsonl(path: Path) -> list[str]:
    """Return sorted unique non-empty label strings from a reviews JSONL file."""
    labels: set[str] = set()
    for obj in iter_jsonl_objects(path, log_errors=False):
        raw = obj.get("labels")
        if not isinstance(raw, list):
            continue
        for lab in raw:
            s = str(lab).strip()
            if s:
                labels.add(s)
    return sorted(labels)


def _plattenlabel_row_sets_and_album_index(
    path: Path,
) -> tuple[list[frozenset[str]], dict[str, set[int]], int]:
    """Build per-row label sets and label -> album index sets from reviews JSONL."""
    row_label_sets: list[frozenset[str]] = []
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        raw = obj.get("labels")
        seen_in_row: set[str] = set()
        if isinstance(raw, list):
            for lab in raw:
                s = str(lab).strip()
                if s and s not in seen_in_row:
                    seen_in_row.add(s)
        row_label_sets.append(frozenset(seen_in_row))

    n_reviews = len(row_label_sets)
    label_to_album_indices: dict[str, set[int]] = {}
    for i, labs in enumerate(row_label_sets):
        for lab in labs:
            label_to_album_indices.setdefault(lab, set()).add(i)
    return row_label_sets, label_to_album_indices, n_reviews


def plattenlabel_album_count_buckets_from_reviews_jsonl(
    path: Path,
    *,
    min_albums_exclusive: int = PLATTENLABEL_INDIVIDUAL_LIST_MIN_ALBUMS,
) -> tuple[list[str], list[str], int]:
    """Split labels into individual list vs rare bucket by album count.

    Returns ``(frequent_by_count_then_name, rare_sorted_a_z, n_reviews)``.
    """
    _, label_to_album_indices, n_reviews = _plattenlabel_row_sets_and_album_index(
        path,
    )
    if n_reviews == 0:
        return [], [], 0

    if not label_to_album_indices:
        return [], [], n_reviews

    threshold = int(min_albums_exclusive)
    sorted_by_freq = sorted(
        label_to_album_indices.keys(),
        key=lambda lab: (-len(label_to_album_indices[lab]), lab),
    )
    frequent = [
        lab for lab in sorted_by_freq if len(label_to_album_indices[lab]) > threshold
    ]
    frequent_set = frozenset(frequent)
    rare = sorted(lab for lab in label_to_album_indices if lab not in frequent_set)
    return frequent, rare, n_reviews
