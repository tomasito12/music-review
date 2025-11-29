from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Any

# Adjust this if your metadata lives elsewhere
DEFAULT_METADATA_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "metadata.jsonl"
)


def load_metadata(path: Path | str = DEFAULT_METADATA_PATH) -> list[dict[str, Any]]:
    """Load all metadata records from a JSONL file."""
    path = Path(path)
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # You could log this if you want
                continue
            if isinstance(record, dict):
                records.append(record)

    return records


def _count_field_values(
    metadata: Iterable[dict[str, Any]],
    field: str,
) -> Counter[str]:
    """Generic helper: count values in a given field.

    Supports:
    - field as list/iterable of strings
    - field as single string
    """
    counter: Counter[str] = Counter()

    for record in metadata:
        values = record.get(field)
        if not values:
            continue

        # Single string
        if isinstance(values, str):
            counter[values] += 1
            continue

        # Iterable of values
        try:
            for value in values:
                if not value:
                    continue
                counter[str(value)] += 1
        except TypeError:
            # Not iterable: count as single value
            counter[str(values)] += 1

    return counter


def get_genre_counts(
    metadata: Iterable[dict[str, Any]],
    field_name: str = "genres",
) -> list[tuple[str, int]]:
    """Return a sorted list of (genre, count).

    Sorted by:
    - descending count
    - then alphabetically by genre
    """
    counter = _count_field_values(metadata, field_name)
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def get_raw_tag_counts(
    metadata: Iterable[dict[str, Any]],
    field_name: str = "raw_tags",
) -> list[tuple[str, int]]:
    """Return a sorted list of (raw_tag, count).

    This is the function you asked for explicitly.
    """
    counter = _count_field_values(metadata, field_name)
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def print_genre_counts(metadata_path: Path | str = DEFAULT_METADATA_PATH) -> None:
    """Load metadata and print all genres with counts to stdout."""
    metadata = load_metadata(metadata_path)
    genre_counts = get_genre_counts(metadata)

    for genre, count in genre_counts:
        print(f"{genre}: {count}")

def print_raw_tags(metadata_path: Path | str = DEFAULT_METADATA_PATH, top_n: int | None = None) -> None:
    metadata = load_metadata(metadata_path)
    raw_tag_counts = get_raw_tag_counts(metadata)

    # Example: look at the top 20 most frequent raw tags
    for tag, count in raw_tag_counts[:top_n or len(raw_tag_counts)]:
        print(tag, count)


if __name__ == "__main__":
    # When run as a script: print all genres with counts
    #print_genre_counts()
    print_raw_tags()