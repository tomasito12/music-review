"""Metadata JSONL loading with imputed-over-raw preference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from music_review.data_access.paths import metadata_imputed_path, metadata_path
from music_review.io.jsonl import load_jsonl_as_map


def resolve_metadata_path(
    *,
    imputed: str | Path | None = None,
    raw: str | Path | None = None,
) -> Path:
    """Pick imputed metadata when present, otherwise raw metadata path."""
    imputed_p = Path(imputed) if imputed is not None else metadata_imputed_path()
    if imputed_p.exists():
        return imputed_p
    return Path(raw) if raw is not None else metadata_path()


def load_metadata_map(
    *,
    imputed: str | Path | None = None,
    raw: str | Path | None = None,
) -> dict[int, dict[str, Any]]:
    """Load review_id -> metadata row, preferring imputed over raw metadata."""
    path = resolve_metadata_path(imputed=imputed, raw=raw)
    if not path.exists():
        return {}
    return load_jsonl_as_map(path, id_key="review_id", log_errors=False)
