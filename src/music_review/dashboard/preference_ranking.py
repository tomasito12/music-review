"""Rank reviews using the same preference score as the recommendations dashboard."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    REFERENCE_POSITION_W_MIN,
    get_recommendation_overall_weights,
    normalize_overall_weights,
)
from music_review.dashboard.recommendation_scoring import (
    blend_purity_breadth,
    breadth_raw_from_selected_community_masses,
    community_spectrum_norm_batch,
    gated_community_spectrum,
    normalize_coverage_batch,
    overall_score,
    percentile_rank_normalize_batch,
    purity_max_weighted_share,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
)
from music_review.domain.models import Review
from music_review.pipeline.retrieval.reference_graph import (
    reference_community_position_masses,
)

RES_KEY = "res_10"


def global_breadth_norm_by_review_id(
    all_reviews: Sequence[Review],
    *,
    memberships: dict[str, dict[str, str]],
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
) -> dict[int, float]:
    """Perzentil-normierte Abdeckungsbreite ``breadth_norm`` ueber **alle** Reviews.

    Entspricht :func:`percentile_rank_normalize_batch` angewandt auf die Liste der
    ``breadth_raw``-Werte des gesamten Korpus (gleiche Formel wie im
    Empfehlungsflow, aber Referenzmenge = alle Alben in ``all_reviews``).

    Leeres ``selected_comms`` oder leere Review-Liste -> leeres Dict.
    """
    if not selected_comms or not all_reviews:
        return {}
    breadth_raws: list[float] = []
    ids: list[int] = []
    for review in all_reviews:
        ref_masses = reference_community_position_masses(
            review,
            memberships,
            res_key=RES_KEY,
            w_min=REFERENCE_POSITION_W_MIN,
        )
        b_raw = breadth_raw_from_selected_community_masses(
            ref_masses,
            selected_comms,
            weights_raw,
        )
        breadth_raws.append(float(b_raw))
        ids.append(int(review.id))
    norms = percentile_rank_normalize_batch(breadth_raws)
    if len(norms) != len(ids):
        return {}
    return {ids[i]: norms[i] for i in range(len(ids))}


def _overall_weights_from_filter_settings(
    filter_settings: Mapping[str, Any],
) -> tuple[float, float, float]:
    fs = filter_settings
    a = fs.get("overall_weight_alpha")
    b = fs.get("overall_weight_beta")
    c = fs.get("overall_weight_gamma")
    if a is not None and b is not None and c is not None:
        return normalize_overall_weights(float(a), float(b), float(c))
    return get_recommendation_overall_weights()


def _preference_score_rows_sorted(
    reviews: Sequence[Review],
    *,
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    memberships: dict[str, dict[str, str]],
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
    filter_settings: Mapping[str, Any],
    rng: random.Random | None = None,
    apply_serendipity: bool = True,
    global_breadth_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Internal: sorted rows with ``score`` (=S_a), norms, and ``overall_score``."""
    rows: list[dict[str, Any]] = []
    crossover_w = float(
        filter_settings.get(
            "community_spectrum_crossover",
            RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
        )
    )
    sort_mode = str(filter_settings.get("sort_mode", "Deterministisch"))
    serendipity = float(filter_settings.get("serendipity", 0.0))

    for review in reviews:
        obj = affinity_by_review_id.get(int(review.id))
        entries_any: list[Any] = []
        if obj is not None and isinstance(obj.get("communities"), dict):
            raw = obj["communities"].get(RES_KEY)
            if isinstance(raw, list):
                entries_any = raw

        s = 0.0
        max_wv = 0.0
        for entry in entries_any:
            if not isinstance(entry, dict):
                continue
            cid = str(entry.get("id"))
            if cid not in selected_comms:
                continue
            score_val = entry.get("score")
            if not isinstance(score_val, (int, float)):
                continue
            val = float(score_val)
            w = float(weights_raw.get(cid, 1.0))
            contrib = w * val
            s += contrib
            if val > 0:
                max_wv = max(max_wv, contrib)

        ref_masses = reference_community_position_masses(
            review,
            memberships,
            res_key=RES_KEY,
            w_min=REFERENCE_POSITION_W_MIN,
        )
        breadth_raw = breadth_raw_from_selected_community_masses(
            ref_masses,
            selected_comms,
            weights_raw,
        )
        purity_raw = purity_max_weighted_share(max_wv, s)

        rows.append(
            {
                "review": review,
                "_s": s,
                "_purity_raw": purity_raw,
                "_breadth_raw": breadth_raw,
            },
        )

    if not rows:
        return []

    alpha, beta, gamma = _overall_weights_from_filter_settings(filter_settings)
    purity_list = [float(r["_purity_raw"]) for r in rows]
    breadth_list = [float(r["_breadth_raw"]) for r in rows]
    if global_breadth_norm_by_review_id is None:
        purity_norms, breadth_norms, spec_norm_list = community_spectrum_norm_batch(
            purity_list,
            breadth_list,
            crossover_weight=crossover_w,
        )
    else:
        purity_norms = normalize_coverage_batch(purity_list)
        gmap = global_breadth_norm_by_review_id
        breadth_norms = [float(gmap.get(int(item["review"].id), 1.0)) for item in rows]
        lam = max(0.0, min(1.0, crossover_w))
        spec_norm_list = [
            blend_purity_breadth(p, b, crossover_weight=lam)
            for p, b in zip(purity_norms, breadth_norms, strict=True)
        ]

    for item, p_n, b_n, spec_n in zip(
        rows,
        purity_norms,
        breadth_norms,
        spec_norm_list,
        strict=True,
    ):
        review = item["review"]
        rn = rating_to_unit_interval(
            review.rating,
            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        s_a = float(item["_s"])
        item["review_id"] = int(review.id)
        item["score"] = s_a
        item["rating_norm"] = rn
        item["purity_norm"] = float(p_n)
        item["breadth_norm"] = float(b_n)
        item["community_spectrum_norm"] = float(spec_n)
        spec_eff, gate = gated_community_spectrum(float(spec_n), s_a)
        item["spectrum_matching_gate"] = gate
        item["community_spectrum_effective"] = spec_eff
        item["overall_score"] = overall_score(
            s_a,
            rn,
            spec_eff,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        item["alpha"] = alpha
        item["beta"] = beta
        item["gamma"] = gamma
        del item["_s"]
        del item["_purity_raw"]
        del item["_breadth_raw"]

    rows.sort(
        key=lambda x: (-float(x["overall_score"]), -int(x["review"].id)),
    )

    if apply_serendipity and sort_mode == "Serendipity" and serendipity > 0.0:
        n_items = len(rows)
        ser_rng = rng if rng is not None else random.Random()
        for i, item in enumerate(rows):
            item["_sk"] = serendipity_rank_sort_key(
                i,
                serendipity=serendipity,
                rng=ser_rng,
                n_items=n_items,
            )
        rows.sort(key=lambda x: float(x["_sk"]))
        for item in rows:
            item.pop("_sk", None)

    return rows


def preference_ranked_rows(
    reviews: Sequence[Review],
    *,
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    memberships: dict[str, dict[str, str]],
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
    filter_settings: Mapping[str, Any],
    rng: random.Random | None = None,
    apply_serendipity: bool = True,
    global_breadth_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Like :func:`rank_reviews_by_saved_preferences` but returns score rows for UI.

    Each dict includes ``review``, ``review_id``, ``score`` (``S_a``),
    ``overall_score``, ``community_spectrum_norm``, ``rating_norm``,
    ``purity_norm``, ``breadth_norm``, and ``alpha`` / ``beta`` / ``gamma``.
    Empty list if ``selected_comms`` is empty.

    If ``apply_serendipity`` is False, the list stays sorted by ``overall_score``
    only (ignores ``sort_mode`` / ``serendipity`` in ``filter_settings``).

    If ``global_breadth_norm_by_review_id`` is set, ``breadth_norm`` (Abdeckungs-
    perzentil) is taken from that map — typically built with
    :func:`global_breadth_norm_by_review_id` over **all** corpus reviews; otherwise
    it is computed only within the current ``reviews`` batch (Empfehlungsliste).
    """
    if not selected_comms:
        return []
    return _preference_score_rows_sorted(
        reviews,
        affinity_by_review_id=affinity_by_review_id,
        memberships=memberships,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
        filter_settings=filter_settings,
        rng=rng,
        apply_serendipity=apply_serendipity,
        global_breadth_norm_by_review_id=global_breadth_norm_by_review_id,
    )


def rank_reviews_by_saved_preferences(
    reviews: Sequence[Review],
    *,
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    memberships: dict[str, dict[str, str]],
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
    filter_settings: Mapping[str, Any],
    rng: random.Random | None = None,
    apply_serendipity: bool = True,
    global_breadth_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[Review]:
    """Sort reviews by the same overall score as ``_compute_recommendations``.

    Unlike the recommendations list, **no** album is dropped: items without hits
    on selected communities keep ``s_a = 0`` and sort lower. Year / rating /
    ``score_min`` / ``score_max`` are **not** applied as hard filters here so the
    “newest N” tile count stays stable.

    If ``selected_comms`` is empty, returns ``list(reviews)`` unchanged.

    When ``apply_serendipity`` is True (default), Serendipity (when
    ``sort_mode == "Serendipity"`` and ``serendipity > 0``) uses the same
    rank-mix keys as the recommendations flow; pass ``rng`` for tests, else a
    fresh :class:`random.Random` is used.

    See :func:`preference_ranked_rows` for ``global_breadth_norm_by_review_id``.
    """
    if not selected_comms:
        return list(reviews)
    rows = _preference_score_rows_sorted(
        reviews,
        affinity_by_review_id=affinity_by_review_id,
        memberships=memberships,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
        filter_settings=filter_settings,
        rng=rng,
        apply_serendipity=apply_serendipity,
        global_breadth_norm_by_review_id=global_breadth_norm_by_review_id,
    )
    return [r["review"] for r in rows]
