"""Tests for update batch backfill from review first_seen_at."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from music_review.io.backfill_update_batches import (
    backfill_update_batches_from_reviews,
    cluster_review_ids_by_first_seen,
)


def test_cluster_review_ids_by_first_seen_groups_close_timestamps() -> None:
    """Reviews seen within one scrape window become one batch."""
    batches = cluster_review_ids_by_first_seen(
        [
            (10, datetime(2026, 7, 1, 10, 0, tzinfo=UTC)),
            (11, datetime(2026, 7, 1, 10, 5, tzinfo=UTC)),
            (12, datetime(2026, 7, 1, 14, 0, tzinfo=UTC)),
        ],
    )

    assert len(batches) == 2
    assert batches[0].review_ids == (10, 11)
    assert batches[1].review_ids == (12,)


def test_backfill_update_batches_from_reviews_writes_jsonl(tmp_path: Path) -> None:
    """Backfill writes inferred batches from review first_seen_at."""
    reviews_path = tmp_path / "reviews.jsonl"
    output_path = tmp_path / "update_batches.jsonl"
    rows = [
        {
            "id": 101,
            "url": "https://example.com/101",
            "artist": "A",
            "album": "B",
            "text": "t",
            "first_seen_at": "2026-07-01T10:00:00Z",
        },
        {
            "id": 102,
            "url": "https://example.com/102",
            "artist": "C",
            "album": "D",
            "text": "t",
            "first_seen_at": "2026-07-01T10:05:00Z",
        },
    ]
    reviews_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    batches = backfill_update_batches_from_reviews(
        reviews_path,
        output_path=output_path,
    )

    assert len(batches) == 1
    assert batches[0].review_ids == (101, 102)
    assert output_path.is_file()
