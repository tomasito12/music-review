"""Tests for community tag helpers."""

from __future__ import annotations

from music_review.application.community_tags import community_tags_from_entries


def test_community_tags_from_entries_filters_by_minimum_affinity() -> None:
    entries = [
        {"id": "C001", "score": 0.8},
        {"id": "C002", "score": 0.15},
        {"id": "C003", "score": 0.05},
    ]

    tags = community_tags_from_entries(
        entries,
        label_for_id=lambda community_id: community_id,
        selected_community_ids={"C001"},
    )

    assert [tag["id"] for tag in tags] == ["C001", "C002"]
    assert tags[0]["matched"] is True
    assert tags[1]["matched"] is False


def test_community_tags_from_entries_keeps_all_tags_above_threshold() -> None:
    entries = [
        {"id": "C001", "score": 0.5},
        {"id": "C002", "score": 0.4},
        {"id": "C003", "score": 0.3},
        {"id": "C004", "score": 0.2},
    ]

    tags = community_tags_from_entries(
        entries,
        label_for_id=lambda community_id: community_id,
    )

    assert len(tags) == 4
