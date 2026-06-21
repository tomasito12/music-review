"""Community graph artifacts: memberships, clusters, and labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from music_review.data_access.paths import (
    communities_res_10_path,
    community_broad_categories_res_10_path,
    community_genre_labels_res_10_path,
    community_memberships_path,
)
from music_review.io.jsonl import iter_jsonl_objects


def load_artist_communities(
    path: str | Path | None = None,
) -> dict[str, dict[str, str]]:
    """Load artist_id -> communities from ``community_memberships.jsonl``.

    Returns an empty dict if the file is missing.
    """
    mp = Path(path) if path is not None else community_memberships_path()
    result: dict[str, dict[str, str]] = {}
    if not mp.exists():
        return result
    for obj in iter_jsonl_objects(mp, log_errors=False):
        artist_id = obj.get("artist_id")
        comms = obj.get("communities")
        if isinstance(artist_id, str) and isinstance(comms, dict):
            result[artist_id] = {
                str(k): str(v) for k, v in comms.items() if isinstance(v, str)
            }
    return result


def load_communities_res_10(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load resolution-10 communities with top artists."""
    p = Path(path) if path is not None else communities_res_10_path()
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    comms = data.get("communities")
    if not isinstance(comms, list):
        return []
    return [c for c in comms if isinstance(c, dict) and c.get("id")]


def load_genre_labels_res_10(path: str | Path | None = None) -> dict[str, str]:
    """Load LLM-assigned genre labels for communities (res_10)."""
    p = Path(path) if path is not None else community_genre_labels_res_10_path()
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return {}
    mapping: dict[str, str] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        label = item.get("genre_label")
        if cid is None or not label:
            continue
        mapping[str(cid)] = str(label)
    return mapping


def load_broad_categories_res_10(
    path: str | Path | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    """Load broad categories and per-community mappings.

    Returns (category names, community_id -> [broad_category, ...]).
    """
    p = Path(path) if path is not None else community_broad_categories_res_10_path()
    if not p.exists():
        return [], {}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], {}
    cats = data.get("broad_categories")
    if not isinstance(cats, list):
        cats = []
    cats = [str(c) for c in cats if isinstance(c, str)]
    raw_mappings = data.get("mappings")
    if not isinstance(raw_mappings, list):
        return cats, {}
    mapping: dict[str, list[str]] = {}
    for item in raw_mappings:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        bc = item.get("broad_categories")
        if isinstance(cid, str) and isinstance(bc, list):
            mapping[cid] = [str(c) for c in bc]
    return cats, mapping


def load_communities_res_file(path: Path | str) -> tuple[list[dict[str, Any]], float]:
    """Load communities from a ``communities_res_*.json`` file.

    Returns ``(communities list, resolution)``. Raises if missing or invalid.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Communities file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    resolution = float(data.get("resolution", 0))
    communities = data.get("communities")
    if not isinstance(communities, list):
        msg = "Expected 'communities' array in JSON."
        raise ValueError(msg)
    return communities, resolution


def load_existing_genre_labels(path: Path | str) -> dict[str, str]:
    """Load ``community_id`` -> ``genre_label`` from a genre-labels JSON file."""
    return load_genre_labels_res_10(path)
