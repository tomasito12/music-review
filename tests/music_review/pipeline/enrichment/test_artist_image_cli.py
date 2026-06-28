"""Tests for the artist image CLI."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.enrichment import artist_image_cli


def test_resolve_targets_from_review_id(tmp_path: Path) -> None:
    """CLI resolves one artist from metadata via review id."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        json.dumps(
            {
                "review_id": 42,
                "artist": "Radiohead",
                "artist_mbid": "mbid-rh",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    args = artist_image_cli._build_parser().parse_args(
        ["--review-id", "42", "--reviews", str(metadata_path), "--dry-run"],
    )

    assert artist_image_cli._resolve_targets(args) == [("mbid-rh", "Radiohead")]
