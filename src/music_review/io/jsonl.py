# music_review/io/jsonl.py

"""Low-level JSONL read/write helpers."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def iter_jsonl_objects(
    path: Path,
    *,
    log_errors: bool = True,
) -> Iterator[dict[str, Any]]:
    """Iterate over JSON objects, one per line. Skips empty lines and invalid JSON."""
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                if log_errors:
                    logger.warning(
                        "Skipping invalid JSON line %d in %s: %s",
                        line_number,
                        path,
                        exc,
                    )
                continue
            if isinstance(obj, dict):
                yield obj


def load_ids_from_jsonl(
    path: Path,
    id_key: str = "id",
    *,
    log_errors: bool = True,
) -> set[int]:
    """Load all integer IDs from a JSONL file. Skips lines without a valid ID."""
    ids: set[int] = set()
    for obj in iter_jsonl_objects(path, log_errors=log_errors):
        val = obj.get(id_key)
        if isinstance(val, int):
            ids.add(val)
    return ids


def load_jsonl_as_map(
    path: Path,
    id_key: str = "id",
    *,
    log_errors: bool = True,
) -> dict[int, dict[str, Any]]:
    """Load JSONL into ID-to-dict mapping. Later entries overwrite earlier."""
    result: dict[int, dict[str, Any]] = {}
    for obj in iter_jsonl_objects(path, log_errors=log_errors):
        val = obj.get(id_key)
        if isinstance(val, int):
            result[val] = obj
    return result


def append_jsonl_line(path: Path, obj: dict[str, Any]) -> None:
    """Append a single JSON object as one line to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, objects: Iterable[dict[str, Any]]) -> None:
    """Write objects to a JSONL file, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in objects:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
