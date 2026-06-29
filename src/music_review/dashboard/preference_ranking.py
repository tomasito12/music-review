"""Rank reviews using the same preference score as the recommendations dashboard."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

from music_review.config import (
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    get_recommendation_overall_weights,
    normalize_overall_weights,
)
from music_review.dashboard.recommendation_scoring import (
    album_style_breadth_norm_for_review_ids,
    effective_style_diversity_from_affinity_entries,
    global_album_style_breadth_norm_by_review_id,
    overall_score,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
    style_fit_norm_for_review_ids,
    weighted_style_fit_raw,
)
from music_review.dashboard.recommendation_scoring import (
    global_style_fit_norm_by_review_id as corpus_style_fit_norm_by_review_id,
)
from music_review.domain.models import Review

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


def global_style_fit_norm_for_profile(
    affinity_by_review_id: Mapping[int, Mapping[str, Any]],
    *,
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
    res_key: str = RES_KEY,
) -> dict[int, float]:
    """Corpus-wide percentile norms for weighted style fit for one taste profile."""
    return corpus_style_fit_norm_by_review_id(
        affinity_by_review_id,
        selected_comms=selected_comms,
        weights_raw=weights_raw,
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
    global_style_fit_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Internal: sorted rows with style-fit, breadth, and overall score."""
    _ = memberships
    corpus_style_fit_norm = global_style_fit_norm_by_review_id
    if corpus_style_fit_norm is None:
        corpus_style_fit_norm = global_style_fit_norm_for_profile(
            affinity_by_review_id,
            selected_comms=selected_comms,
            weights_raw=weights_raw,
        )
    corpus_breadth_norm = global_breadth_norm_by_review_id
    if corpus_breadth_norm is None:
        corpus_breadth_norm = global_album_style_breadth_norm_by_review_id(
            affinity_by_review_id,
        )
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
                "_style_fit_raw": style_fit_raw,
                "_style_diversity_n_eff": style_diversity_n_eff,
            },
        )

    if not rows:
        return []

    raw_by_review_id = {
        int(row["review"].id): float(row["_style_fit_raw"]) for row in rows
    }
    style_fits = style_fit_norm_for_review_ids(
        [int(row["review"].id) for row in rows],
        raw_by_review_id,
        global_norm_by_review_id=corpus_style_fit_norm,
    )
    for row, style_fit in zip(rows, style_fits, strict=True):
        row["_style_fit"] = style_fit

    n_eff_by_review_id = {
        int(row["review"].id): float(row["_style_diversity_n_eff"]) for row in rows
    }
    style_breadth_norms = album_style_breadth_norm_for_review_ids(
        [int(row["review"].id) for row in rows],
        n_eff_by_review_id,
        global_norm_by_review_id=corpus_breadth_norm,
    )

    alpha, beta, gamma = _overall_weights_from_filter_settings(filter_settings)
    for item, style_breadth in zip(rows, style_breadth_norms, strict=True):
        review = item["review"]
        rating_norm = rating_to_unit_interval(
            review.rating,
            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        style_fit = float(item["_style_fit"])
        item["review_id"] = int(review.id)
        item["style_fit_raw"] = float(item["_style_fit_raw"])
        item["style_diversity_n_eff"] = float(item["_style_diversity_n_eff"])
        item["album_style_breadth"] = style_breadth
        item["score"] = style_fit
        item["rating_norm"] = rating_norm
        item["overall_score"] = overall_score(
            style_fit,
            rating_norm,
            style_breadth,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        item["alpha"] = alpha
        item["beta"] = beta
        item["gamma"] = gamma
        del item["_style_fit_raw"]
        del item["_style_diversity_n_eff"]
        del item["_style_fit"]

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
    global_style_fit_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Return preference-ranked score rows for UI and services.

    Each dict includes ``review``, ``review_id``, ``score`` (corpus-percentile
    style fit), ``overall_score``, ``rating_norm``, ``album_style_breadth``,
    ``style_diversity_n_eff``, and ``alpha`` / ``beta`` / ``gamma``.
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
        global_style_fit_norm_by_review_id=global_style_fit_norm_by_review_id,
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
    global_style_fit_norm_by_review_id: Mapping[int, float] | None = None,
) -> list[Review]:
    """Sort reviews by overall score without hard album filters."""
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
        global_style_fit_norm_by_review_id=global_style_fit_norm_by_review_id,
    )
    return [r["review"] for r in rows]
