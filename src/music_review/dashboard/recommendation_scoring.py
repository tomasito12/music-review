"""Pure functions for recommendation overall score (dashboard)."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from music_review.config import RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW


def percentile_rank_normalize_batch(raw_values: list[float]) -> list[float]:
    """Map values to [0, 1] from ordinal rank (average rank for ties).

    Lowest raw value in the batch maps to **0**, highest to **1**; spacing follows
    rank order (uniform over sorted positions), not linear in the raw magnitude.
    Tied values share the same average rank before scaling.

    Empty input -> []. Single value -> [1.0] (same sentinel as all-equal min-max).
    """
    if not raw_values:
        return []
    n = len(raw_values)
    if n == 1:
        return [1.0]
    indexed = sorted(enumerate(raw_values), key=lambda x: (x[1], x[0]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            orig_idx = indexed[k][0]
            ranks[orig_idx] = avg_rank
        i = j
    r_min = min(ranks)
    r_max = max(ranks)
    if r_max <= r_min:
        return [1.0] * n
    return [(r - r_min) / (r_max - r_min) for r in ranks]


def effective_plattentests_rating(
    rating: float | int | None,
    *,
    default_when_missing: float,
) -> float:
    """Return rating on 0-10 scale; use default when ``rating`` is None."""
    if rating is None:
        return float(default_when_missing)
    return float(rating)


def rating_to_unit_interval(
    rating: float | int | None,
    *,
    default_on_10_scale: float,
) -> float:
    """Map Plattentests rating (0-10, or missing) to [0, 1] via default."""
    r = effective_plattentests_rating(
        rating,
        default_when_missing=default_on_10_scale,
    )
    r_clamped = max(0.0, min(10.0, r))
    return r_clamped / 10.0


def affinity_vector_from_entries(
    entries: Sequence[Mapping[str, object]],
) -> dict[str, float]:
    """Build a sparse album affinity vector from ``res_*`` community entries."""
    out: dict[str, float] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        cid = entry.get("id")
        score_val = entry.get("score")
        if cid is None or not isinstance(score_val, (int, float)):
            continue
        affinity = float(score_val)
        if affinity > 0.0:
            out[str(cid)] = affinity
    return out


def album_style_proportions_from_entries(
    entries: Sequence[Mapping[str, object]],
) -> tuple[float, ...]:
    """Return normalized album style shares (positive affinities summing to 1)."""
    masses = affinity_vector_from_entries(entries)
    if not masses:
        return ()
    total_mass = sum(masses.values())
    if total_mass <= 0.0:
        return ()
    return tuple(mass / total_mass for mass in masses.values())


def shannon_entropy_from_proportions(proportions: Sequence[float]) -> float:
    """Shannon entropy in nats; zero-mass components are ignored."""
    entropy = 0.0
    for proportion in proportions:
        p = float(proportion)
        if p <= 0.0:
            continue
        entropy -= p * math.log(p)
    return entropy


def effective_style_count_from_proportions(proportions: Sequence[float]) -> float:
    """Effective number of styles: ``N_eff = exp(H)`` from album proportions."""
    positive = [
        float(proportion) for proportion in proportions if float(proportion) > 0.0
    ]
    if len(positive) <= 1:
        return 1.0
    return math.exp(shannon_entropy_from_proportions(positive))


def effective_style_diversity_from_affinity_entries(
    entries: Sequence[Mapping[str, object]],
) -> float:
    """Effective Shannon diversity ``N_eff = exp(H)`` from album community shares."""
    proportions = album_style_proportions_from_entries(entries)
    if not proportions:
        return 1.0
    return effective_style_count_from_proportions(proportions)


def global_album_style_breadth_norm_by_review_id(
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    *,
    res_key: str = "res_10",
) -> dict[int, float]:
    """Percentile-normalize album style diversity across the corpus.

    Uses effective Shannon diversity ``N_eff`` per album. Lowest ``N_eff`` in the
    corpus maps to ``0``, highest to ``1`` (ordinal ranks, ties averaged).
    """
    if not affinity_by_review_id:
        return {}
    review_ids: list[int] = []
    n_eff_values: list[float] = []
    for review_id, affinity_row in affinity_by_review_id.items():
        entries_any = affinity_row.get("communities")
        entries: list[Mapping[str, object]] = []
        if isinstance(entries_any, Mapping):
            raw = entries_any.get(res_key)
            if isinstance(raw, list):
                entries = [entry for entry in raw if isinstance(entry, Mapping)]
        review_ids.append(int(review_id))
        n_eff_values.append(
            effective_style_diversity_from_affinity_entries(entries),
        )
    norms = percentile_rank_normalize_batch(n_eff_values)
    if len(norms) != len(review_ids):
        return {}
    return {review_ids[i]: norms[i] for i in range(len(review_ids))}


def album_style_breadth_norm_for_review_ids(
    review_ids: Sequence[int],
    n_eff_by_review_id: Mapping[int, float],
    *,
    global_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[float]:
    """Resolve percentile-normalized style breadth for one ordered review list."""
    if global_norm_by_review_id is not None:
        return [
            float(global_norm_by_review_id.get(int(review_id), 0.0))
            for review_id in review_ids
        ]
    n_eff_values = [
        float(n_eff_by_review_id[int(review_id)]) for review_id in review_ids
    ]
    return percentile_rank_normalize_batch(n_eff_values)


def _affinity_entries_from_row(
    affinity_row: Mapping[str, Any],
    *,
    res_key: str = "res_10",
) -> list[Mapping[str, object]]:
    """Return valid community affinity entries from one indexed affinity row."""
    entries_any = affinity_row.get("communities")
    if not isinstance(entries_any, Mapping):
        return []
    raw = entries_any.get(res_key)
    if not isinstance(raw, list):
        return []
    return [entry for entry in raw if isinstance(entry, Mapping)]


def global_style_fit_norm_by_review_id(
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    *,
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
    res_key: str = "res_10",
) -> dict[int, float]:
    """Percentile-normalize weighted style fit across the corpus for one profile.

    Lowest raw fit in the corpus maps to ``0``, highest to ``1`` (ordinal ranks,
    ties averaged). Profile-specific because fit uses selected communities and
    stored weights.
    """
    if not affinity_by_review_id:
        return {}
    review_ids: list[int] = []
    raw_values: list[float] = []
    for review_id, affinity_row in affinity_by_review_id.items():
        entries = _affinity_entries_from_row(affinity_row, res_key=res_key)
        review_ids.append(int(review_id))
        raw_values.append(
            weighted_style_fit_raw(
                entries,
                selected_comms=selected_comms,
                weights_raw=weights_raw,
            ),
        )
    norms = percentile_rank_normalize_batch(raw_values)
    if len(norms) != len(review_ids):
        return {}
    return {review_ids[i]: norms[i] for i in range(len(review_ids))}


def style_fit_norm_for_review_ids(
    review_ids: Sequence[int],
    raw_by_review_id: Mapping[int, float],
    *,
    global_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[float]:
    """Resolve percentile-normalized style fit for one ordered review list."""
    if global_norm_by_review_id is not None:
        return [
            float(global_norm_by_review_id.get(int(review_id), 0.0))
            for review_id in review_ids
        ]
    raw_values = [float(raw_by_review_id[int(review_id)]) for review_id in review_ids]
    return percentile_rank_normalize_batch(raw_values)


def weighted_style_fit_raw(
    entries: Sequence[Mapping[str, object]],
    *,
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
    default_weight: float = RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
) -> float:
    """Weighted album-style fit: sum of album shares times profile weights.

    Uses every positive album community (shares sum to 1). Communities not in
    ``selected_comms`` contribute profile weight 0. Selected communities use
    stored weights, or ``default_weight`` when unset.
    """
    album_masses = affinity_vector_from_entries(entries)
    if not album_masses:
        return 0.0
    total_mass = sum(album_masses.values())
    if total_mass <= 0.0:
        return 0.0
    selected = {str(community_id) for community_id in selected_comms}
    fit = 0.0
    for community_id, mass in album_masses.items():
        share = mass / total_mass
        if community_id in selected:
            weight = float(weights_raw.get(community_id, default_weight))
        else:
            weight = 0.0
        fit += share * weight
    return max(0.0, min(1.0, fit))


def style_fit_batch_normalized(raw_values: list[float]) -> list[float]:
    """Map raw style-fit values to [0, 1] by dividing by the batch maximum."""
    if not raw_values:
        return []
    maximum = max(float(value) for value in raw_values)
    if maximum <= 0.0:
        return [0.0] * len(raw_values)
    return [float(value) / maximum for value in raw_values]


def overall_score(
    style_fit_norm: float,
    rating_norm: float,
    style_breadth_norm: float,
    *,
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """Linear combination of three normalized scores in ``[0, 1]``.

    ``alpha`` weights style fit, ``beta`` plattentests rating, ``gamma`` album
    style breadth (percentile-normalized Shannon diversity ``N_eff`` over the corpus).
    """
    return alpha * style_fit_norm + beta * rating_norm + gamma * style_breadth_norm


def serendipity_rank_sort_key(
    rank_index: int,
    *,
    serendipity: float,
    rng: random.Random,
    n_items: int,
) -> float:
    """Sort key for gradual shuffle vs. deterministic ranking."""
    if n_items <= 1:
        return 0.0
    s = max(0.0, min(1.0, float(serendipity)))
    r_norm = float(rank_index) / float(n_items - 1)
    u = rng.random()
    return (1.0 - s) * r_norm + s * u
