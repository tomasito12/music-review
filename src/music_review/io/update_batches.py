"""Persist and load production scrape batches for Aktuell filtering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from music_review.data_access.paths import update_batches_path
from music_review.io.jsonl import append_jsonl_line, iter_jsonl_objects


@dataclass(frozen=True, slots=True)
class UpdateBatch:
    """One production scrape run and the review ids discovered in it."""

    run_at: datetime
    review_ids: tuple[int, ...]

    @property
    def count(self) -> int:
        """Number of reviews discovered in this batch."""
        return len(self.review_ids)


def _parse_run_at(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp from JSON."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_review_ids(value: object) -> tuple[int, ...]:
    """Parse a list of integer review ids from JSON."""
    if not isinstance(value, list):
        return ()
    ids: list[int] = []
    for item in value:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            ids.append(item)
        elif isinstance(item, float) and item.is_integer():
            ids.append(int(item))
    return tuple(ids)


def update_batch_from_raw(raw: Mapping[str, Any]) -> UpdateBatch | None:
    """Convert one JSON object into an UpdateBatch, or None if invalid."""
    run_at = _parse_run_at(raw.get("run_at"))
    review_ids = _parse_review_ids(raw.get("review_ids"))
    if run_at is None or not review_ids:
        return None
    return UpdateBatch(run_at=run_at, review_ids=review_ids)


def update_batch_to_raw(batch: UpdateBatch) -> dict[str, Any]:
    """Serialize one batch for JSONL storage."""
    return {
        "run_at": batch.run_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "review_ids": list(batch.review_ids),
        "count": batch.count,
    }


def load_update_batches(path: str | Path | None = None) -> tuple[UpdateBatch, ...]:
    """Load scrape batches ordered oldest to newest."""
    file_path = Path(update_batches_path() if path is None else path)
    if not file_path.is_file():
        return ()

    batches: list[UpdateBatch] = []
    for raw in iter_jsonl_objects(file_path, log_errors=False):
        if not isinstance(raw, dict):
            continue
        batch = update_batch_from_raw(raw)
        if batch is not None:
            batches.append(batch)
    batches.sort(key=lambda item: item.run_at)
    return tuple(batches)


def append_update_batch(
    review_ids: Sequence[int],
    *,
    path: str | Path | None = None,
    run_at: datetime | None = None,
) -> UpdateBatch | None:
    """Append one scrape batch when new review ids were discovered."""
    unique_ids = tuple(dict.fromkeys(int(review_id) for review_id in review_ids))
    if not unique_ids:
        return None

    batch = UpdateBatch(
        run_at=(run_at or datetime.now(UTC)).astimezone(UTC),
        review_ids=unique_ids,
    )
    file_path = Path(update_batches_path() if path is None else path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl_line(file_path, update_batch_to_raw(batch))
    return batch


def review_ids_for_last_n_batches(
    batches: Sequence[UpdateBatch],
    rounds: int,
) -> frozenset[int]:
    """Collect review ids from the most recent N scrape batches."""
    if rounds < 1 or not batches:
        return frozenset()
    selected = batches[-rounds:]
    ids: set[int] = set()
    for batch in selected:
        ids.update(batch.review_ids)
    return frozenset(ids)


def has_update_batch_history(batches: Sequence[UpdateBatch]) -> bool:
    """Return whether at least one valid scrape batch is stored."""
    return len(batches) > 0
