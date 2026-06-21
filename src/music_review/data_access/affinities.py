"""Album-to-community affinity JSONL loading and projections."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from music_review.data_access.paths import album_community_affinities_path
from music_review.io.jsonl import iter_jsonl_objects

RES_KEY_DEFAULT = "res_10"


def _is_valid_affinity_row(obj: dict[str, Any]) -> bool:
    return "review_id" in obj and "communities" in obj


def load_affinities_raw(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load all valid album affinity rows from JSONL."""
    p = Path(path) if path is not None else album_community_affinities_path()
    if not p.is_file():
        return []
    records: list[dict[str, Any]] = []
    for obj in iter_jsonl_objects(p, log_errors=False):
        if isinstance(obj, dict) and _is_valid_affinity_row(obj):
            records.append(obj)
    return records


def affinities_by_review_id(
    path: str | Path | None = None,
) -> dict[int, dict[str, Any]]:
    """Map review_id to full affinity row."""
    out: dict[int, dict[str, Any]] = {}
    for obj in load_affinities_raw(path):
        rid = obj.get("review_id")
        if isinstance(rid, int):
            out[rid] = obj
    return out


def affinities_list(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return affinity rows as a list (alias for canonical load)."""
    return load_affinities_raw(path)


def top_communities_per_review(
    *,
    path: str | Path | None = None,
    top_k: int = 5,
    res_key: str = RES_KEY_DEFAULT,
) -> dict[int, list[tuple[str, float]]]:
    """Map review_id to top-k community (id, score) pairs for one resolution."""
    result: dict[int, list[tuple[str, float]]] = {}
    for obj in load_affinities_raw(path):
        review_id = obj.get("review_id")
        comms = (obj.get("communities") or {}).get(res_key)
        if not isinstance(review_id, int) or not isinstance(comms, list):
            continue
        items: list[tuple[str, float]] = []
        for entry in comms:
            if not isinstance(entry, dict):
                continue
            cid = entry.get("id")
            score = entry.get("score")
            if isinstance(cid, str) and isinstance(score, (int, float)):
                items.append((cid, float(score)))
        if not items:
            continue
        items.sort(key=lambda t: t[1], reverse=True)
        result[review_id] = items[:top_k]
    return result
