"""Compute album-to-community affinity scores from reference lists."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from music_review.config import REFERENCE_POSITION_W_MIN
from music_review.data_access.communities import load_artist_communities
from music_review.domain.reference_masses import reference_community_position_masses
from music_review.io.reviews_jsonl import load_reviews_from_jsonl


def compute_album_affinities(
    reviews_path: str | Path,
    memberships_path: str | Path,
    resolutions: list[float],
    w_min: float = REFERENCE_POSITION_W_MIN,
    top_k_per_res: int | None = None,
    threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """Compute soft album→community affinities from reference lists.

    For each review, we:
      - take the ordered reference list
      - for each reference and each resolution, look up the artist's community ID
      - add position_weight(i, n, w_min) to that community's score
      - normalise scores per resolution to sum to 1.0
      - optionally drop communities with score below `threshold`
      - optionally keep only top_k_per_res communities

    Returns a list of rows with:
      {
        "review_id": int,
        "artist": str,
        "album": str,
        "url": str,
        "communities": {
          "res_10": [{"id": "C001", "score": 0.62}, ...]
        }
      }
    """
    reviews = load_reviews_from_jsonl(Path(reviews_path))

    memberships = load_artist_communities(memberships_path)
    if not Path(memberships_path).exists():
        raise FileNotFoundError(f"Memberships file not found: {memberships_path}")

    rows: list[dict[str, Any]] = []
    res_keys: dict[float, str] = {}
    for res in resolutions:
        if float(res).is_integer():
            res_keys[res] = f"res_{int(res)}"
        else:
            res_keys[res] = f"res_{res}"

    for review in reviews:
        res_scores: dict[float, dict[str, float]] = {}
        for res in resolutions:
            res_key = res_keys[res]
            res_scores[res] = reference_community_position_masses(
                review,
                memberships,
                res_key=res_key,
                w_min=w_min,
            )
        if not any(res_scores.values()):
            continue

        communities_out: dict[str, list[dict[str, Any]]] = {}
        for res in resolutions:
            scores = res_scores[res]
            if not scores:
                continue
            total = sum(scores.values())
            if total <= 0:
                continue
            items = [(cid, score / total) for cid, score in scores.items()]
            # Filter by threshold
            if threshold > 0.0:
                items = [item for item in items if item[1] >= threshold]
            if not items:
                continue
            # Sort by score desc
            items.sort(key=lambda x: x[1], reverse=True)
            if top_k_per_res is not None and top_k_per_res > 0:
                items = items[:top_k_per_res]
            key = res_keys[res]
            communities_out[key] = [{"id": cid, "score": score} for cid, score in items]

        if not communities_out:
            continue

        rows.append(
            {
                "review_id": review.id,
                "artist": review.artist,
                "album": review.album,
                "url": review.url,
                "communities": communities_out,
            }
        )

    return rows
