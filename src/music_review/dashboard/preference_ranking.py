"""Rank reviews using the same preference score as the recommendations dashboard."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    REFERENCE_POSITION_W_MIN,
    get_recommendation_overall_weights,
    normalize_overall_weights,
)
from music_review.dashboard.recommendation_scoring import (
    album_style_breadth_norm_for_review_ids,
    breadth_raw_from_selected_community_masses,
    effective_style_diversity_from_affinity_entries,
    global_album_style_breadth_norm_by_review_id,
    overall_score,
    purity_max_weighted_share,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
    style_fit_batch_normalized,
    weighted_style_fit_raw,
)
from music_review.domain.models import Review
from music_review.domain.reference_masses import reference_community_position_masses

RES_KEY = "res_10"


def global_breadth_norm_by_review_id(
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    *,
    res_key: str = RES_KEY,
) -> dict[int, float]:
    """Corpus-wide percentile norms for album Shannon diversity ``N_eff``.

    Lowest ``N_eff`` in the corpus maps to ``0``, highest to ``1``.
    """
    return global_album_style_breadth_norm_by_review_id(
        affinity_by_review_id,
        res_key=res_key,
    )


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
            w = float(weights_raw.get(cid, RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW))
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

        style_fit_raw = weighted_style_fit_raw(
            entries_any,
            selected_comms=selected_comms,
            weights_raw=weights_raw,
        )
        style_diversity_n_eff = effective_style_diversity_from_affinity_entries(
            entries_any,
        )

        rows.append(
            {
                "review": review,
                "_s": s,
                "_style_fit_raw": style_fit_raw,
                "_style_diversity_n_eff": style_diversity_n_eff,
                "_purity_raw": purity_raw,
                "_breadth_raw": breadth_raw,
            },
        )

    if not rows:
        return []

    style_fits = style_fit_batch_normalized(
        [float(row["_style_fit_raw"]) for row in rows],
    )
    for row, style_fit in zip(rows, style_fits, strict=True):
        row["_style_fit"] = style_fit

    n_eff_by_review_id = {
        int(row["review"].id): float(row["_style_diversity_n_eff"]) for row in rows
    }
    style_breadth_norms = album_style_breadth_norm_for_review_ids(
        [int(row["review"].id) for row in rows],
        n_eff_by_review_id,
        global_norm_by_review_id=global_breadth_norm_by_review_id,
    )

    alpha, beta, gamma = _overall_weights_from_filter_settings(filter_settings)
    for item, style_breadth in zip(rows, style_breadth_norms, strict=True):
        review = item["review"]
        rn = rating_to_unit_interval(
            review.rating,
            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        s_a = float(item["_s"])
        style_fit = float(item["_style_fit"])
        item["review_id"] = int(review.id)
        item["s_a"] = s_a
        item["style_fit_raw"] = float(item["_style_fit_raw"])
        item["style_diversity_n_eff"] = float(item["_style_diversity_n_eff"])
        item["album_style_breadth"] = style_breadth
        item["style_breadth_norm"] = style_breadth
        item["score"] = style_fit
        item["rating_norm"] = rn
        item["breadth_norm"] = style_breadth
        item["community_spectrum_norm"] = style_breadth
        item["community_spectrum_effective"] = style_breadth
        item["spectrum_matching_gate"] = 1.0
        item["overall_score"] = overall_score(
            style_fit,
            rn,
            style_breadth,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        item["alpha"] = alpha
        item["beta"] = beta
        item["gamma"] = gamma
        item["purity_raw"] = float(item["_purity_raw"])
        item["breadth_raw"] = float(item["_breadth_raw"])
        del item["_s"]
        del item["_style_fit_raw"]
        del item["_style_diversity_n_eff"]
        del item["_style_fit"]
        del item["_purity_raw"]
        del item["_breadth_raw"]

    rows.sort(
        key=lambda x: (
            -float(x["overall_score"]),
            -float(x["score"]),
            -int(x["review"].id),
        ),
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

    Each dict includes ``review``, ``review_id``, ``score`` (batch-normalized
    style fit), ``s_a`` (legacy weighted sum), ``overall_score``,
    ``community_spectrum_norm``, ``rating_norm``, ``album_style_breadth``,
    ``purity_raw``, ``breadth_raw``, ``purity_norm``, ``breadth_norm``, and
    ``alpha`` / ``beta`` / ``gamma``.
    Empty list if ``selected_comms`` is empty.

    If ``apply_serendipity`` is False, the list stays sorted by ``overall_score``
    only (ignores ``sort_mode`` / ``serendipity`` in ``filter_settings``).

    ``global_breadth_norm_by_review_id`` supplies corpus-wide percentile norms for
    album Shannon diversity. When omitted, norms are computed within the batch.
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
