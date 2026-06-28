"""Recommendation service independent of Streamlit session state."""

from __future__ import annotations

import logging
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from music_review.application.community_tags import community_tags_from_entries
from music_review.application.models import TasteProfile
from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    REFERENCE_POSITION_W_MIN,
    normalize_overall_weights,
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
from music_review.domain.reference_masses import reference_community_position_masses

LOGGER = logging.getLogger(__name__)

RES_KEY = "res_10"


@dataclass(frozen=True, slots=True)
class RecommendationInputs:
    """All data needed to score archive recommendations."""

    reviews: Sequence[Review]
    metadata: Mapping[int, Mapping[str, Any]]
    affinities: Sequence[Mapping[str, Any]]
    memberships: dict[str, dict[str, str]]
    communities: Sequence[Mapping[str, Any]]
    genre_labels: Mapping[str, str]
    plattenlabels: Sequence[str] = ()
    year_floor: int = 1990
    year_cap: int = 2100


@dataclass(frozen=True, slots=True)
class RecommendationService:
    """Compute recommendations from a taste profile and injected corpus data."""

    inputs: RecommendationInputs
    logger: logging.Logger = field(default=LOGGER)

    def compute_archive_recommendations(
        self,
        profile: TasteProfile,
        *,
        rng: random.Random | None = None,
    ) -> list[dict[str, Any]]:
        """Return archive recommendation rows matching the legacy dashboard shape."""
        selected_comms = selected_communities_from_profile(profile)
        if not selected_comms:
            return []
        if not self.inputs.reviews or not self.inputs.affinities:
            return []

        settings = profile.filter_settings
        requested_year_min = settings.year_min
        if requested_year_min is None:
            requested_year_min = self.inputs.year_floor
        requested_year_max = settings.year_max
        if requested_year_max is None:
            requested_year_max = self.inputs.year_cap
        year_min, year_max = _clamp_year_bounds(
            requested_year_min,
            requested_year_max,
            year_floor=self.inputs.year_floor,
            year_cap=self.inputs.year_cap,
        )
        rating_min, rating_max = _clamp_rating_range(
            settings.rating_min,
            settings.rating_max,
        )

        review_index: dict[int, Review] = {int(r.id): r for r in self.inputs.reviews}
        comm_by_id: dict[str, Mapping[str, Any]] = {
            str(c.get("id")): c for c in self.inputs.communities if c.get("id")
        }

        candidates = self._candidate_rows(
            profile,
            selected_comms=selected_comms,
            review_index=review_index,
            comm_by_id=comm_by_id,
            year_min=year_min,
            year_max=year_max,
            rating_min=rating_min,
            rating_max=rating_max,
        )
        if not candidates:
            return []

        _apply_overall_scores(candidates, profile)
        candidates.sort(key=lambda x: float(x["overall_score"]), reverse=True)
        if settings.sort_mode == "discovery" and settings.serendipity > 0.0:
            _apply_serendipity(candidates, settings.serendipity, rng=rng)
        return candidates

    def _candidate_rows(
        self,
        profile: TasteProfile,
        *,
        selected_comms: set[str],
        review_index: Mapping[int, Review],
        comm_by_id: Mapping[str, Mapping[str, Any]],
        year_min: int,
        year_max: int,
        rating_min: float,
        rating_max: float,
    ) -> list[dict[str, Any]]:
        """Build pre-ranking candidate rows after hard filters."""
        settings = profile.filter_settings
        candidates: list[dict[str, Any]] = []
        for obj in self.inputs.affinities:
            entries_any = _affinity_entries(obj)
            if not entries_any:
                continue
            row = self._candidate_row_for_affinity(
                obj,
                entries_any=entries_any,
                profile=profile,
                selected_comms=selected_comms,
                review_index=review_index,
                comm_by_id=comm_by_id,
                year_min=year_min,
                year_max=year_max,
                rating_min=rating_min,
                rating_max=rating_max,
            )
            if row is None:
                continue
            score = float(row["score"])
            if settings.score_min <= score <= settings.score_max:
                candidates.append(row)
        return candidates

    def _candidate_row_for_affinity(
        self,
        obj: Mapping[str, Any],
        *,
        entries_any: Sequence[Mapping[str, Any]],
        profile: TasteProfile,
        selected_comms: set[str],
        review_index: Mapping[int, Review],
        comm_by_id: Mapping[str, Mapping[str, Any]],
        year_min: int,
        year_max: int,
        rating_min: float,
        rating_max: float,
    ) -> dict[str, Any] | None:
        """Return one candidate row, or None when it fails hard filters."""
        s, k_hits, max_wv = _selected_affinity_score(
            entries_any,
            selected_comms=selected_comms,
            weights_raw=profile.community_weights_raw,
        )
        if k_hits == 0:
            return None

        review_id_val = obj.get("review_id")
        if not isinstance(review_id_val, int):
            return None
        review = review_index.get(int(review_id_val))
        if review is None:
            return None

        if not _plattenlabel_filter_passes(
            review.labels,
            profile.filter_settings.plattenlabel_selection,
            self.inputs.plattenlabels,
        ):
            return None

        eff_rating = effective_plattentests_rating(
            review.rating,
            default_when_missing=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        if eff_rating < rating_min or eff_rating > rating_max:
            return None

        year_val = review.release_year
        if year_val is None and review.release_date is not None:
            year_val = review.release_date.year
        if year_val is not None and not (year_min <= year_val <= year_max):
            return None

        ref_masses = reference_community_position_masses(
            review,
            self.inputs.memberships,
            res_key=RES_KEY,
            w_min=REFERENCE_POSITION_W_MIN,
        )
        breadth_raw = breadth_raw_from_selected_community_masses(
            ref_masses,
            selected_comms,
            profile.community_weights_raw,
        )
        meta = self.inputs.metadata.get(review_id_val) or {}
        return {
            "review_id": review_id_val,
            "artist": review.artist,
            "album": review.album,
            "score": s,
            "k_hits": k_hits,
            "purity_raw": purity_max_weighted_share(max_wv, s),
            "breadth_raw": breadth_raw,
            "hits_pct": 100.0 * breadth_raw,
            "rating": review.rating,
            "rating_effective": eff_rating,
            "year": year_val,
            "release_date": review.release_date,
            "labels": _format_record_labels(meta.get("labels"), review.labels),
            "url": review.url,
            "text": review.text,
            "top_communities": community_tags_from_entries(
                entries_any,
                label_for_id=lambda community_id: _community_display_label(
                    community_id,
                    self.inputs.genre_labels,
                    comm_by_id.get(community_id),
                ),
                selected_community_ids=selected_comms,
            ),
        }


def selected_communities_from_profile(profile: TasteProfile) -> set[str]:
    """Return the canonical selected community IDs for one profile."""
    if profile.selected_communities:
        return set(profile.selected_communities)
    return set(profile.artist_flow_selected_communities) | set(
        profile.genre_flow_selected_communities,
    )


def _affinity_entries(obj: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return valid res_10 affinity entries from one raw affinity object."""
    comms = obj.get("communities", {})
    if not isinstance(comms, Mapping):
        return []
    entries_any = comms.get(RES_KEY)
    if not isinstance(entries_any, list):
        return []
    return [
        entry
        for entry in entries_any
        if isinstance(entry, Mapping) and isinstance(entry.get("score"), (int, float))
    ]


def _selected_affinity_score(
    entries: Sequence[Mapping[str, Any]],
    *,
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
) -> tuple[float, int, float]:
    """Return raw selected-community score, hit count, and strongest contribution."""
    score = 0.0
    hits = 0
    max_weighted_value = 0.0
    for entry in entries:
        cid = str(entry.get("id"))
        if cid not in selected_comms:
            continue
        score_val = entry.get("score")
        if not isinstance(score_val, (int, float)):
            continue
        affinity = float(score_val)
        weight = float(
            weights_raw.get(cid, RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW),
        )
        contribution = weight * affinity
        score += contribution
        if affinity > 0:
            hits += 1
            max_weighted_value = max(max_weighted_value, contribution)
    return score, hits, max_weighted_value


def _apply_overall_scores(
    candidates: list[dict[str, Any]],
    profile: TasteProfile,
) -> None:
    """Add normalized score components and overall score to each candidate."""
    settings = profile.filter_settings
    alpha, beta, gamma = normalize_overall_weights(
        settings.overall_weight_alpha,
        settings.overall_weight_beta,
        settings.overall_weight_gamma,
    )
    purity_list = [float(c["purity_raw"]) for c in candidates]
    breadth_list = [float(c["breadth_raw"]) for c in candidates]
    purity_norms, breadth_norms, spec_norm_list = community_spectrum_norm_batch(
        purity_list,
        breadth_list,
        crossover_weight=settings.community_spectrum_crossover,
    )
    for item, p_n, b_n, spec_n in zip(
        candidates,
        purity_norms,
        breadth_norms,
        spec_norm_list,
        strict=True,
    ):
        rating_norm = rating_to_unit_interval(
            item["rating"],
            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        )
        spec_eff, gate = gated_community_spectrum(float(spec_n), float(item["score"]))
        item["purity_norm"] = p_n
        item["breadth_norm"] = b_n
        item["community_spectrum_norm"] = spec_n
        item["spectrum_matching_gate"] = gate
        item["community_spectrum_effective"] = spec_eff
        item["rating_norm"] = rating_norm
        item["overall_score"] = overall_score(
            float(item["score"]),
            rating_norm,
            spec_eff,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )


def _apply_serendipity(
    candidates: list[dict[str, Any]],
    serendipity: float,
    *,
    rng: random.Random | None,
) -> None:
    """Sort candidates with the legacy serendipity rank-mix behavior."""
    ser_rng = rng if rng is not None else random.Random()
    n_items = len(candidates)
    for index, item in enumerate(candidates):
        item["_serendipity_key"] = serendipity_rank_sort_key(
            index,
            serendipity=serendipity,
            rng=ser_rng,
            n_items=n_items,
        )
    candidates.sort(key=lambda x: float(x["_serendipity_key"]))
    for item in candidates:
        item.pop("_serendipity_key", None)


def _clamp_year_bounds(
    year_min: Any,
    year_max: Any,
    *,
    year_floor: int,
    year_cap: int,
) -> tuple[int, int]:
    """Clamp year bounds to the available corpus range."""
    try:
        lo = int(year_min)
    except (TypeError, ValueError):
        lo = year_floor
    try:
        hi = int(year_max)
    except (TypeError, ValueError):
        hi = year_cap
    lo = max(year_floor, min(lo, year_cap))
    hi = max(year_floor, min(hi, year_cap))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _clamp_rating_range(rating_min: Any, rating_max: Any) -> tuple[float, float]:
    """Clamp plattentests.de rating bounds to 0..10."""
    try:
        lo = float(rating_min)
    except (TypeError, ValueError):
        lo = 0.0
    try:
        hi = float(rating_max)
    except (TypeError, ValueError):
        hi = 10.0
    lo = max(0.0, min(10.0, lo))
    hi = max(0.0, min(10.0, hi))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _plattenlabel_filter_passes(
    album_labels: Sequence[str] | None,
    selection: Sequence[str] | None,
    all_labels: Sequence[str],
) -> bool:
    """Whether an album passes the Plattenlabel expert filter."""
    if not all_labels:
        return True
    if selection is None:
        return True
    all_set = frozenset(str(x).strip() for x in all_labels if str(x).strip())
    sel_set = frozenset(str(x).strip() for x in selection if str(x).strip())
    if sel_set == all_set:
        return True
    raw_album = list(album_labels) if album_labels else []
    album_set = frozenset(str(x).strip() for x in raw_album if str(x).strip())
    if not sel_set:
        return len(album_set) == 0
    if not album_set:
        return True
    return bool(album_set & sel_set)


def _format_record_labels(
    metadata_labels: Any,
    review_labels: Sequence[str] | None,
) -> str:
    """Build comma-separated Plattenlabel text for recommendation cards."""
    if isinstance(metadata_labels, str):
        text = metadata_labels.strip()
        if text:
            return text
    if isinstance(metadata_labels, list):
        items = [str(item).strip() for item in metadata_labels if str(item).strip()]
        if items:
            return ", ".join(items)
    if review_labels:
        return ", ".join(
            str(item).strip() for item in review_labels if str(item).strip()
        )
    return ""


def _community_display_label(
    community_id: str,
    genre_labels: Mapping[str, str],
    community: Mapping[str, Any] | None,
) -> str:
    """Human-readable name for a music cluster."""
    genre_label = genre_labels.get(community_id)
    if genre_label:
        return genre_label
    if community is not None:
        centroid = community.get("centroid")
        if centroid:
            return str(centroid)
    return "Stil-Cluster"
