"""Reference-list position weights and per-community mass aggregation."""

from __future__ import annotations

from music_review.config import REFERENCE_POSITION_W_MIN
from music_review.domain.models import Review


def normalize_reference_artist_name(name: str) -> str:
    """Normalize artist name for node identity (lowercase, strip)."""
    return name.strip().lower() if name else ""


def position_weight(
    position_1based: int,
    num_references: int,
    w_min: float = REFERENCE_POSITION_W_MIN,
) -> float:
    """Weight for a reference by its position in the album's reference list.

    First reference gets 1.0, last gets w_min (never 0). Linear decay in between.
    """
    if num_references <= 0:
        return w_min
    if num_references == 1:
        return 1.0
    return w_min + (1.0 - w_min) * (num_references - position_1based) / (
        num_references - 1
    )


def reference_community_position_masses(
    review: Review,
    memberships: dict[str, dict[str, str]],
    *,
    res_key: str,
    w_min: float = REFERENCE_POSITION_W_MIN,
) -> dict[str, float]:
    """Sum position weights per community ID for one resolution key."""
    refs = [r for r in review.references if isinstance(r, str) and r.strip()]
    if not refs:
        return {}
    n = len(refs)
    scores: dict[str, float] = {}
    for idx, ref in enumerate(refs):
        pos = idx + 1
        w = position_weight(pos, n, w_min=w_min)
        artist_key = normalize_reference_artist_name(ref)
        if not artist_key:
            continue
        artist_comms = memberships.get(artist_key)
        if not artist_comms:
            continue
        cid = artist_comms.get(res_key)
        if not cid:
            continue
        scores[cid] = scores.get(cid, 0.0) + w
    return scores
