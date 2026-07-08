"""Tests for update batch backfill from review first_seen_at and hourly logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from music_review.io.backfill_update_batches import (
    append_latest_batch_from_hourly_log,
    backfill_update_batches_from_hourly_log,
    backfill_update_batches_from_reviews,
    cluster_review_ids_by_first_seen,
    parse_batches_from_hourly_log,
    review_ids_in_inclusive_range,
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


def test_review_ids_in_inclusive_range_filters_to_corpus() -> None:
    """Only review ids present in the corpus are returned."""
    assert review_ids_in_inclusive_range(
        10,
        12,
        known_review_ids=frozenset({10, 12}),
    ) == (
        10,
        12,
    )


def test_parse_batches_from_hourly_log_reads_timestamped_lines(tmp_path: Path) -> None:
    """Hourly log lines with scrape ranges become ordered batches."""
    log_path = tmp_path / "hourly-update.log"
    log_path.write_text(
        "\n".join(
            [
                "2026-07-01 10:00:01,123 [INFO] music_review.pipeline.orchestration: "
                "Found 2 new reviews (10-11). Continuing with enrichment.",
                "2026-07-01 14:00:01,456 [INFO] music_review.pipeline.orchestration: "
                "Found 1 new reviews (12-12). Continuing with enrichment.",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    batches = parse_batches_from_hourly_log(
        log_path,
        known_review_ids=frozenset({10, 11, 12}),
    )

    assert len(batches) == 2
    assert batches[0].review_ids == (10, 11)
    assert batches[0].run_at == datetime(2026, 7, 1, 10, 0, 1, 123000, tzinfo=UTC)
    assert batches[1].review_ids == (12,)


def test_backfill_update_batches_from_hourly_log_writes_jsonl(tmp_path: Path) -> None:
    """Hourly log backfill writes merged batches to JSONL."""
    reviews_path = tmp_path / "reviews.jsonl"
    output_path = tmp_path / "update_batches.jsonl"
    log_path = tmp_path / "hourly-update.log"
    reviews_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": review_id,
                    "url": f"https://example.com/{review_id}",
                    "artist": "A",
                    "album": "B",
                    "text": "t",
                },
            )
            for review_id in (101, 102)
        )
        + "\n",
        encoding="utf-8",
    )
    log_path.write_text(
        "2026-07-01 10:00:01,000 [INFO] pkg: Found 2 new reviews (101-102). "
        "Continuing with enrichment.\n",
        encoding="utf-8",
    )

    batches = backfill_update_batches_from_hourly_log(
        log_path,
        reviews_path=reviews_path,
        output_path=output_path,
    )

    assert len(batches) == 1
    assert batches[0].review_ids == (101, 102)
    assert output_path.is_file()


def test_append_latest_batch_from_hourly_log_appends_only_newest(
    tmp_path: Path,
) -> None:
    """Latest-only mode appends the final scrape batch from the log."""
    reviews_path = tmp_path / "reviews.jsonl"
    output_path = tmp_path / "update_batches.jsonl"
    log_path = tmp_path / "hourly-update.log"
    reviews_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": review_id,
                    "url": f"https://example.com/{review_id}",
                    "artist": "A",
                    "album": "B",
                    "text": "t",
                },
            )
            for review_id in (10, 11, 12)
        )
        + "\n",
        encoding="utf-8",
    )
    log_path.write_text(
        "\n".join(
            [
                "2026-07-01 10:00:01,000 [INFO] pkg: Found 2 new reviews (10-11). "
                "Continuing with enrichment.",
                "2026-07-01 14:00:01,000 [INFO] pkg: Found 1 new reviews (12-12). "
                "Continuing with enrichment.",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    batch = append_latest_batch_from_hourly_log(
        log_path,
        reviews_path=reviews_path,
        output_path=output_path,
    )

    assert batch is not None
    assert batch.review_ids == (12,)
    assert output_path.read_text(encoding="utf-8").count('"review_ids"') == 1
