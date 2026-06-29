"""Pure functions for recommendation overall score (dashboard)."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION,
)


def gini_coefficient(masses: Sequence[float]) -> float:
    """Discrete Gini coefficient for nonnegative masses (scale-invariant).

    ``0`` = perfectly equal masses; ``1`` = maximal inequality in the standard sense.
    Empty sequence or ``sum(masses) <= 0`` returns ``1.0`` (treat as maximal
    inequality so ``1 - gini`` yields zero breadth). A single positive mass returns
    ``0.0``.
    """
    x = [float(v) for v in masses if float(v) >= 0.0]
    n = len(x)
    if n == 0:
        return 1.0
    s = sum(x)
    if s <= 0.0:
        return 1.0
    if n == 1:
        return 0.0
    x_sorted = sorted(x)
    weighted = sum((i + 1) * xi for i, xi in enumerate(x_sorted))
    gini = (2.0 * weighted) / (n * s) - (n + 1.0) / n
    return min(1.0, max(0.0, gini))


def breadth_raw_from_selected_community_masses(
    raw_mass_by_cid: Mapping[str, float],
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
) -> float:
    """Inverted Gini breadth: ``1 - Gini`` over user-weighted masses on selection only.

    ``raw_mass_by_cid`` is unnormalised position-weight sum per community ID
    (see ``reference_community_position_masses`` in ``reference_graph``).
    Only communities in ``selected_comms`` appear in the Gini vector (sorted ``cid``
    order); reference mass on other communities is ignored.

    Returns a value in ``[0, 1]``.
    """
    ordered = sorted(str(c) for c in selected_comms)
    if not ordered:
        return 0.0
    masses = [
        float(weights_raw.get(c, RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW))
        * float(raw_mass_by_cid.get(c, 0.0))
        for c in ordered
    ]
    g = gini_coefficient(masses)
    return max(0.0, min(1.0, 1.0 - g))


def normalize_coverage_batch(raw_values: list[float]) -> list[float]:
    """Min-max normalize coverage values to [0, 1] within this batch.

    Same index as input. If all values are equal, returns 1.0 for each entry
    (so the gamma term does not zero out the entire list).
    """
    if not raw_values:
        return []
    lo = min(raw_values)
    hi = max(raw_values)
    if hi <= lo:
        return [1.0] * len(raw_values)
    return [(x - lo) / (hi - lo) for x in raw_values]


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
        # Average 1-based rank for the tie block covering sorted positions i..j-1.
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


def purity_max_weighted_share(max_weighted_affinity: float, s_a_total: float) -> float:
    """Share of the strongest selected community in the weighted affinity sum (0-1).

    Near 1 when one community dominates (blütenrein); lower when mass spreads.
    """
    if s_a_total <= 0.0:
        return 0.0
    return min(1.0, max_weighted_affinity / s_a_total)


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


def user_preference_vector(
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
    *,
    default_weight: float = RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
) -> dict[str, float]:
    """Sparse user taste vector: weights on selected communities, zero elsewhere."""
    return {
        str(community_id): float(
            weights_raw.get(str(community_id), default_weight),
        )
        for community_id in selected_comms
    }


def cosine_similarity_sparse(
    left: Mapping[str, float],
    right: Mapping[str, float],
) -> float:
    """Cosine similarity of two sparse vectors over the union of their keys."""
    if not left or not right:
        return 0.0
    keys = set(left) | set(right)
    dot = sum(float(left.get(key, 0.0)) * float(right.get(key, 0.0)) for key in keys)
    norm_left = math.sqrt(sum(float(value) ** 2 for value in left.values()))
    norm_right = math.sqrt(sum(float(value) ** 2 for value in right.values()))
    if norm_left <= 0.0 or norm_right <= 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_left * norm_right)))


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


def matching_style_proportions_from_entries(
    entries: Sequence[Mapping[str, object]],
    *,
    selected_comms: Iterable[str],
) -> tuple[float, ...]:
    """Normalized album shares restricted to the profile's selected communities."""
    masses = affinity_vector_from_entries(entries)
    if not masses:
        return ()
    selected = {str(community_id) for community_id in selected_comms}
    matching = {
        community_id: float(mass)
        for community_id, mass in masses.items()
        if community_id in selected and float(mass) > 0.0
    }
    if not matching:
        return ()
    total_mass = sum(matching.values())
    if total_mass <= 0.0:
        return ()
    return tuple(mass / total_mass for mass in matching.values())


def matching_style_breadth_from_affinity_entries(
    entries: Sequence[Mapping[str, object]],
    *,
    selected_comms: Iterable[str],
) -> float:
    """Breadth of how many selected styles match on the album.

    Uses only communities from ``selected_comms`` with positive album affinity.
    A single matching style yields ``0``; several selected styles with meaningful
    shares yield values in ``(0, 1]``.
    """
    proportions = matching_style_proportions_from_entries(
        entries,
        selected_comms=selected_comms,
    )
    if not proportions:
        return 0.0
    n_eff = effective_style_count_from_proportions(proportions)
    if n_eff <= 1.0 or len(proportions) <= 1:
        return 0.0
    return min(1.0, (n_eff - 1.0) / (len(proportions) - 1.0))


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


def aligned_style_cosine_fit_raw(
    entries: Sequence[Mapping[str, object]],
    *,
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
    default_weight: float = RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
) -> float:
    """Deprecated alias for :func:`weighted_style_fit_raw` (cosine removed)."""
    return weighted_style_fit_raw(
        entries,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
        default_weight=default_weight,
    )


def style_fit_batch_normalized(raw_values: list[float]) -> list[float]:
    """Map raw style-fit values to [0, 1] by dividing by the batch maximum."""
    if not raw_values:
        return []
    maximum = max(float(value) for value in raw_values)
    if maximum <= 0.0:
        return [0.0] * len(raw_values)
    return [float(value) / maximum for value in raw_values]


def cosine_fit_from_affinity_entries(
    entries: Sequence[Mapping[str, object]],
    *,
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
) -> float:
    """Weighted style fit (legacy name kept for Score Lab columns)."""
    return weighted_style_fit_raw(
        entries,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
    )


def cosine_fit_from_affinity_row(
    affinity_row: Mapping[str, object] | None,
    *,
    selected_comms: Iterable[str],
    weights_raw: Mapping[str, float],
    res_key: str = "res_10",
) -> float:
    """Cosine fit for one album affinity row, or 0 when data is missing."""
    if affinity_row is None:
        return 0.0
    comms = affinity_row.get("communities")
    if not isinstance(comms, Mapping):
        return 0.0
    entries_any = comms.get(res_key)
    if not isinstance(entries_any, list):
        return 0.0
    return cosine_fit_from_affinity_entries(
        entries_any,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
    )


def album_spectrum_term_from_style_breadth(
    album_style_breadth: float,
    *,
    crossover_weight: float,
) -> tuple[float, float, float]:
    """Blend stylistic purity and breadth for the gamma overall-score term.

    Uses per-album ``album_style_breadth`` over all album communities (entropy-based,
    absolute in [0, 1]). ``crossover_weight`` 0 favors stylistically pure albums;
    1 favors stylistically broad albums.

    Returns ``(spectrum_term, purity_side, breadth_side)``.

    The legacy reference-graph spectrum (:func:`community_spectrum_norm_batch`) remains
    available for Score Lab but is not used in the active ranking path.
    """
    breadth = max(0.0, min(1.0, float(album_style_breadth)))
    purity = 1.0 - breadth
    spectrum = blend_purity_breadth(purity, breadth, crossover_weight=crossover_weight)
    return spectrum, purity, breadth


def blend_purity_breadth(
    purity_raw: float,
    breadth_raw: float,
    *,
    crossover_weight: float,
) -> float:
    """Linear mix of two values in [0, 1] (often pre-normalized batch scores).

    ``crossover_weight`` (lambda): 0 = only first operand (purity / "bluetenrein");
    1 = only second (Cross-Over / breadth). Used after batch normalization of purity
    (min-max) and breadth (percentile ranks); see :func:`community_spectrum_norm_batch`.
    """
    lam = max(0.0, min(1.0, crossover_weight))
    return (1.0 - lam) * purity_raw + lam * breadth_raw


def spectrum_matching_gate(
    s_a: float,
    *,
    half_saturation: float | None = None,
) -> float:
    """Smooth gate ``g(S_a)`` in ``[0, 1)`` to couple spectrum term to matching.

    Uses ``g(s) = s / (s + k)`` with ``k = half_saturation`` when ``k > 0``:
    ``g(0) = 0``, ``g(k) = 0.5``, and ``g -> 1`` for large ``s``.

    If ``half_saturation`` is ``None``, uses
    :data:`music_review.config.RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION`.
    If ``half_saturation <= 0``, returns ``1.0`` (no gating).

    The **effective** spectrum input to :func:`overall_score` is
    ``community_spectrum_norm * g(S_a)``.
    """
    k = (
        float(RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION)
        if half_saturation is None
        else float(half_saturation)
    )
    if k <= 0.0:
        return 1.0
    s = max(0.0, float(s_a))
    return s / (s + k)


def gated_community_spectrum(
    community_spectrum_norm: float,
    s_a: float,
    *,
    half_saturation: float | None = None,
) -> tuple[float, float]:
    """Return ``(effective_spectrum, gate)`` for the overall score."""
    g = spectrum_matching_gate(s_a, half_saturation=half_saturation)
    return (float(community_spectrum_norm) * g, g)


def community_spectrum_norm_batch(
    purity_raw_values: list[float],
    breadth_raw_values: list[float],
    *,
    crossover_weight: float,
) -> tuple[list[float], list[float], list[float]]:
    """Normalize purity (min-max) and breadth (percentile rank), then blend with lambda.

    **Purity** uses min-max over the batch. **Breadth** (inverted-Gini reference
    coverage raw score) uses :func:`percentile_rank_normalize_batch`: lowest -> 0,
    highest -> 1,
    with uniform spacing by rank (ties averaged).

    lambda=0 uses only purity_norm; lambda=1 only breadth_norm. Intermediate values
    mix the two (each in [0, 1]).

    Returns ``(purity_norms, breadth_norms, community_spectrum_norm)``.
    """
    if len(purity_raw_values) != len(breadth_raw_values):
        msg = "purity_raw_values and breadth_raw_values must have the same length"
        raise ValueError(msg)
    p_norm = normalize_coverage_batch(purity_raw_values)
    b_norm = percentile_rank_normalize_batch(breadth_raw_values)
    lam = max(0.0, min(1.0, crossover_weight))
    blended = [
        blend_purity_breadth(p, b, crossover_weight=lam)
        for p, b in zip(p_norm, b_norm, strict=True)
    ]
    return (p_norm, b_norm, blended)


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
    """Sort key for gradual shuffle vs. deterministic ranking.

    Call **after** sorting by true score (best first): ``rank_index=0`` is the top
    album, ``rank_index=n-1`` the worst. Sort **ascending** by this key to get the
    Serendipity order.

    Uses ``key = (1-s) * r_norm + s * U`` with ``r_norm`` in ``[0, 1]`` along the
    list and ``U ~ Uniform(0,1)`` i.i.d. Then ``s=0`` preserves order; ``s=1`` is a
    uniform random permutation (Spearman correlation of old vs. new ranks ~ 0 for
    large ``n``). For ``s`` in between, Spearman rho is **approximately** ``1 - s``
    (not exact for finite ``n``, but matches the intended ``1 -`` correlation
    intuition).
    """
    if n_items <= 1:
        return 0.0
    s = max(0.0, min(1.0, float(serendipity)))
    r_norm = float(rank_index) / float(n_items - 1)
    u = rng.random()
    return (1.0 - s) * r_norm + s * u
