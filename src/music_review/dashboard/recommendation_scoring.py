"""Pure functions for recommendation overall score (dashboard)."""

from __future__ import annotations

import random
from collections.abc import Iterable, Mapping, Sequence

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
    s_a: float,
    rating_norm: float,
    community_term_norm: float,
    *,
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """Linear combination of normalized components (each typically in [0, 1])."""
    return alpha * s_a + beta * rating_norm + gamma * community_term_norm


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
