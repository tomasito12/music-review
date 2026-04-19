"""Shared recommendations computation: filter+score+sort over the album corpus.

Used by:

- The Empfehlungen page (``pages/6_Recommendations_Flow.py``) to render the
  ranked album list.
- The Spotify-Playlists page (``pages/9_Spotify_Playlists.py``, archive mode) to
  build a candidate pool with the same scoring as the Empfehlungen page.

Keeps the data loaders cached (``@st.cache_data``) so repeated calls within a
Streamlit session reuse the parsed JSONL files.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

import streamlit as st
from pages.page_helpers import (
    DEFAULT_PLATTENTESTS_RATING_FILTER_MAX,
    DEFAULT_PLATTENTESTS_RATING_FILTER_MIN,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
    community_display_label,
    format_record_labels_for_card,
    get_selected_communities,
    load_communities_res_10,
    load_community_memberships,
    load_genre_labels_res_10,
    load_sorted_unique_plattenlabels_from_reviews,
    max_release_year_from_corpus,
    min_release_year_from_corpus,
    plattenlabel_filter_passes,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    REFERENCE_POSITION_W_MIN,
    get_recommendation_overall_weights,
    normalize_overall_weights,
    resolve_data_path,
)
from music_review.dashboard.recommendation_scoring import (
    breadth_raw_from_selected_community_masses,
    community_spectrum_norm_batch,
    effective_plattentests_rating,
    gated_community_spectrum,
    overall_score,
    purity_max_weighted_share,
    rating_to_unit_interval,
    serendipity_rank_sort_key,
)
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.pipeline.retrieval.reference_graph import (
    reference_community_position_masses,
)

LOGGER = logging.getLogger(__name__)

# German user-visible sort labels stored verbatim in ``filter_settings["sort_mode"]``.
SORT_MODE_FIXED = "Feste Reihenfolge"
SORT_MODE_RANDOM = "Mit Zufall"

# Legacy values from earlier versions of the Filter Flow are auto-migrated.
SORT_MODE_MIGRATION: dict[str, str] = {
    "Deterministisch": SORT_MODE_FIXED,
    "Serendipity": SORT_MODE_RANDOM,
}


@st.cache_data(ttl=3600)
def load_reviews_and_metadata() -> tuple[list[Review], dict[int, dict[str, Any]]]:
    """Load the corpus reviews plus the (optional) imputed metadata map."""
    reviews_path = resolve_data_path("data/reviews.jsonl")
    imputed_path = resolve_data_path("data/metadata_imputed.jsonl")
    fallback_path = resolve_data_path("data/metadata.jsonl")
    metadata_path = imputed_path if imputed_path.exists() else fallback_path

    if not reviews_path.exists():
        return [], {}

    reviews = load_reviews_from_jsonl(reviews_path)
    metadata: dict[int, dict[str, Any]] = {}
    if metadata_path.exists():
        metadata = load_jsonl_as_map(
            metadata_path,
            id_key="review_id",
            log_errors=False,
        )
    return reviews, metadata


@st.cache_data(ttl=3600)
def load_affinities() -> list[dict[str, Any]]:
    """Load the album-to-community affinity records used for scoring."""
    path = resolve_data_path("data/album_community_affinities.jsonl")
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    for obj in iter_jsonl_objects(p, log_errors=False):
        if isinstance(obj, dict) and "review_id" in obj and "communities" in obj:
            records.append(obj)
    return records


def compute_recommendations() -> list[dict[str, Any]]:
    """Score and sort albums from the current Streamlit session taste settings.

    Reads ``selected_communities``, ``filter_settings`` and ``community_weights_raw``
    from ``st.session_state`` (no extra profile DB read). Returns one dict per
    album that passes filters; each dict contains ``review_id``, ``artist``,
    ``album``, ``score``, ``overall_score``, ``rating``, ``year``, ``url``,
    ``text``, ``top_communities`` and the score breakdown used by the UI.
    """
    selected_comms = get_selected_communities()
    if not selected_comms:
        return []

    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}

    year_cap = max_release_year_from_corpus()
    year_floor = min_release_year_from_corpus()
    year_min, year_max = clamp_year_filter_bounds(
        filter_settings.get("year_min", year_floor),
        filter_settings.get("year_max", year_cap),
        year_cap=year_cap,
        year_floor=year_floor,
    )
    rating_min, rating_max = clamp_plattentests_rating_filter_range(
        filter_settings.get("rating_min", DEFAULT_PLATTENTESTS_RATING_FILTER_MIN),
        filter_settings.get("rating_max", DEFAULT_PLATTENTESTS_RATING_FILTER_MAX),
    )
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))
    sm_raw = str(filter_settings.get("sort_mode", SORT_MODE_FIXED))
    sort_mode = SORT_MODE_MIGRATION.get(sm_raw, sm_raw)
    serendipity = float(filter_settings.get("serendipity", 0.0))
    crossover_w = float(
        filter_settings.get(
            "community_spectrum_crossover",
            RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
        )
    )

    def _overall_weights_from_session() -> tuple[float, float, float]:
        fs = filter_settings
        a = fs.get("overall_weight_alpha")
        b = fs.get("overall_weight_beta")
        c = fs.get("overall_weight_gamma")
        if a is not None and b is not None and c is not None:
            return normalize_overall_weights(float(a), float(b), float(c))
        return get_recommendation_overall_weights()

    reviews, metadata = load_reviews_and_metadata()
    affinities = load_affinities()
    memberships = load_community_memberships()
    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()

    if not reviews or not affinities:
        return []

    platten_all = load_sorted_unique_plattenlabels_from_reviews()
    plat_sel = filter_settings.get("plattenlabel_selection")

    review_index: dict[int, Review] = {int(r.id): r for r in reviews}
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    res_key = "res_10"

    candidates: list[dict[str, Any]] = []

    for obj in affinities:
        comms = obj.get("communities", {})
        if not isinstance(comms, dict):
            continue
        entries_any = comms.get(res_key)
        if not isinstance(entries_any, list):
            continue

        sorted_entries = sorted(
            [
                e
                for e in entries_any
                if isinstance(e, dict) and isinstance(e.get("score"), (int, float))
            ],
            key=lambda e: float(e.get("score", 0.0)),
            reverse=True,
        )
        top_entries = sorted_entries[:3]

        s = 0.0
        k_hits = 0
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
                k_hits += 1
                max_wv = max(max_wv, contrib)

        if k_hits == 0:
            continue
        if not (score_min <= s <= score_max):
            continue

        review_id_val = obj.get("review_id")
        if not isinstance(review_id_val, int):
            continue
        review = review_index.get(int(review_id_val))
        if review is None:
            continue

        if not plattenlabel_filter_passes(review.labels, plat_sel, platten_all):
            continue

        rating_val = review.rating
        eff_rating = effective_plattentests_rating(
            rating_val,
            default_when_missing=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        if eff_rating < rating_min or eff_rating > rating_max:
            continue

        year_val: int | None = None
        if review.release_year is not None:
            year_val = review.release_year
        elif review.release_date is not None:
            year_val = review.release_date.year
        if year_val is not None and not (year_min <= year_val <= year_max):
            continue

        ref_masses = reference_community_position_masses(
            review,
            memberships,
            res_key=res_key,
            w_min=REFERENCE_POSITION_W_MIN,
        )
        breadth_raw = breadth_raw_from_selected_community_masses(
            ref_masses,
            selected_comms,
            weights_raw,
        )
        hits_pct = 100.0 * breadth_raw
        purity_raw = purity_max_weighted_share(max_wv, s)

        meta = metadata.get(review_id_val) or {}
        label_str = format_record_labels_for_card(meta.get("labels"), review.labels)

        top_communities: list[dict[str, Any]] = []
        for e in top_entries:
            cid = str(e.get("id"))
            aff = float(e.get("score", 0.0))
            c_obj = comm_by_id.get(cid)
            label = community_display_label(
                cid,
                genre_labels,
                c_obj if isinstance(c_obj, dict) else None,
            )
            top_communities.append(
                {
                    "id": cid,
                    "label": label,
                    "affinity": aff,
                },
            )

        candidates.append(
            {
                "review_id": review_id_val,
                "artist": review.artist,
                "album": review.album,
                "score": s,
                "k_hits": k_hits,
                "purity_raw": purity_raw,
                "breadth_raw": breadth_raw,
                "hits_pct": hits_pct,
                "rating": rating_val,
                "rating_effective": eff_rating,
                "year": year_val,
                "release_date": review.release_date,
                "labels": label_str,
                "url": review.url,
                "text": review.text,
                "top_communities": top_communities,
            },
        )

    if not candidates:
        return []

    alpha, beta, gamma = _overall_weights_from_session()
    purity_list = [float(c["purity_raw"]) for c in candidates]
    breadth_list = [float(c["breadth_raw"]) for c in candidates]
    purity_norms, breadth_norms, spec_norm_list = community_spectrum_norm_batch(
        purity_list,
        breadth_list,
        crossover_weight=crossover_w,
    )
    for item, p_n, b_n, spec_n in zip(
        candidates,
        purity_norms,
        breadth_norms,
        spec_norm_list,
        strict=True,
    ):
        rn = rating_to_unit_interval(
            item["rating"],
            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        item["purity_norm"] = p_n
        item["breadth_norm"] = b_n
        item["community_spectrum_norm"] = spec_n
        spec_eff, gate = gated_community_spectrum(
            float(spec_n),
            float(item["score"]),
        )
        item["spectrum_matching_gate"] = gate
        item["community_spectrum_effective"] = spec_eff
        item["rating_norm"] = rn
        item["overall_score"] = overall_score(
            float(item["score"]),
            rn,
            spec_eff,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )

    candidates.sort(key=lambda x: float(x["overall_score"]), reverse=True)
    if sort_mode == SORT_MODE_RANDOM and serendipity > 0.0:
        rng = random.Random()
        n = len(candidates)
        for i, item in enumerate(candidates):
            item["_serendipity_key"] = serendipity_rank_sort_key(
                i,
                serendipity=serendipity,
                rng=rng,
                n_items=n,
            )
        candidates.sort(key=lambda x: float(x["_serendipity_key"]))
        for item in candidates:
            item.pop("_serendipity_key", None)

    return candidates


def archive_playlist_candidates() -> tuple[list[Review], list[dict[str, Any]] | None]:
    """Return reviews and ranked rows from :func:`compute_recommendations`.

    The shape matches what
    :func:`music_review.dashboard.newest_spotify_playlist.build_album_weights`
    expects as ``(reviews, ranked_rows)``: each row contains ``review`` (the
    :class:`Review` object) and ``overall_score`` (float). The order follows the
    Empfehlungen ranking. Returns ``([], None)`` when no candidates are found
    (no taste set, missing data, or filters too strict).
    """
    recs = compute_recommendations()
    if not recs:
        LOGGER.info("archive playlist candidates: no recommendations available")
        return [], None
    reviews_all, _metadata = load_reviews_and_metadata()
    if not reviews_all:
        LOGGER.warning(
            "archive playlist candidates: recommendations present but corpus empty",
        )
        return [], None
    review_index: dict[int, Review] = {int(r.id): r for r in reviews_all}
    reviews_in_order: list[Review] = []
    ranked_rows: list[dict[str, Any]] = []
    for rec in recs:
        rid = rec.get("review_id")
        if not isinstance(rid, int):
            continue
        review = review_index.get(rid)
        if review is None:
            continue
        score_any = rec.get("overall_score")
        score = float(score_any) if isinstance(score_any, (int, float)) else 0.0
        reviews_in_order.append(review)
        ranked_rows.append({"review": review, "overall_score": score})
    if not reviews_in_order:
        LOGGER.warning(
            "archive playlist candidates: recommendations had no resolvable Review",
        )
        return [], None
    LOGGER.info(
        "archive playlist candidates: n_reviews=%s n_ranked_rows=%s",
        len(reviews_in_order),
        len(ranked_rows),
    )
    return reviews_in_order, ranked_rows
