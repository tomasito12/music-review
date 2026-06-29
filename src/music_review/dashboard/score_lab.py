"""Score Lab helpers: ranked rows with full breakdown for internal tuning."""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from music_review.application.community_tags import community_tags_from_entries
from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.application.presets import TASTE_PRESETS
from music_review.application.recommendation_service import (
    RecommendationInputs,
    RecommendationService,
    selected_communities_from_profile,
)
from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    normalize_overall_weights,
)
from music_review.dashboard.preference_ranking import preference_ranked_rows
from music_review.dashboard.recommendation_scoring import cosine_fit_from_affinity_row
from music_review.dashboard.user_profile_store import default_profiles_dir, load_profile
from music_review.domain.models import Review

ScoreLabDataSource = Literal["archive", "review_ids"]

SCORE_LAB_TABLE_COLUMNS: tuple[str, ...] = (
    "rank",
    "review_id",
    "artist",
    "album",
    "score",
    "cosine_fit",
    "rating",
    "rating_norm",
    "purity_raw",
    "breadth_raw",
    "purity_norm",
    "breadth_norm",
    "community_spectrum_norm",
    "spectrum_matching_gate",
    "community_spectrum_effective",
    "alpha",
    "beta",
    "gamma",
    "overall_score",
    "k_hits",
)

_PRESET_COMPARE_FIELDS: tuple[str, ...] = (
    "score_min",
    "score_max",
    "rating_min",
    "rating_max",
    "overall_weight_alpha",
    "overall_weight_beta",
    "overall_weight_gamma",
    "community_spectrum_crossover",
    "sort_mode",
    "serendipity",
)


def parse_review_ids_text(text: str) -> frozenset[int]:
    """Parse comma- or semicolon-separated review IDs; ignore invalid tokens."""
    ids: set[int] = set()
    for part in text.replace(";", ",").split(","):
        token = part.strip()
        if not token:
            continue
        try:
            ids.add(int(token))
        except ValueError:
            continue
    return frozenset(ids)


def guess_matching_preset_id(filter_settings: TasteFilterSettings) -> str | None:
    """Return a preset id when filter settings match a known taste preset."""
    current = {
        field: getattr(filter_settings, field) for field in _PRESET_COMPARE_FIELDS
    }
    for preset in TASTE_PRESETS:
        candidate = {
            field: getattr(preset.filter_settings, field)
            for field in _PRESET_COMPARE_FIELDS
        }
        if candidate == current:
            return preset.id
    return None


def profile_with_lab_overrides(
    profile: TasteProfile,
    *,
    overall_weight_alpha: float,
    overall_weight_beta: float,
    overall_weight_gamma: float,
    community_spectrum_crossover: float,
    score_min: float,
    score_max: float,
) -> TasteProfile:
    """Return a profile copy with lab slider values applied (deterministic sort)."""
    filter_settings = profile.filter_settings.model_copy(
        update={
            "overall_weight_alpha": overall_weight_alpha,
            "overall_weight_beta": overall_weight_beta,
            "overall_weight_gamma": overall_weight_gamma,
            "community_spectrum_crossover": community_spectrum_crossover,
            "score_min": score_min,
            "score_max": score_max,
            "sort_mode": "deterministic",
            "serendipity": 0.0,
        },
    )
    return profile.model_copy(update={"filter_settings": filter_settings})


def affinity_by_review_id(
    affinities: Sequence[Mapping[str, Any]],
) -> dict[int, Mapping[str, Any]]:
    """Index affinity rows by ``review_id``."""
    out: dict[int, Mapping[str, Any]] = {}
    for obj in affinities:
        review_id = obj.get("review_id")
        if isinstance(review_id, int):
            out[int(review_id)] = obj
    return out


def k_hits_for_review(
    affinity_row: Mapping[str, Any] | None,
    *,
    selected_comms: set[str],
) -> int:
    """Count selected communities with a positive affinity score on one album."""
    if affinity_row is None:
        return 0
    comms = affinity_row.get("communities")
    if not isinstance(comms, Mapping):
        return 0
    entries_any = comms.get("res_10")
    if not isinstance(entries_any, list):
        return 0
    hits = 0
    for entry in entries_any:
        if not isinstance(entry, Mapping):
            continue
        cid = str(entry.get("id"))
        if cid not in selected_comms:
            continue
        score_val = entry.get("score")
        if isinstance(score_val, (int, float)) and float(score_val) > 0:
            hits += 1
    return hits


def score_lab_rows_to_csv(
    rows: Sequence[Mapping[str, Any]],
    *,
    delimiter: str = ";",
) -> str:
    """Serialize score-lab table rows to UTF-8 CSV text."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(SCORE_LAB_TABLE_COLUMNS),
        delimiter=delimiter,
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column) for column in SCORE_LAB_TABLE_COLUMNS})
    return buffer.getvalue()


def _effective_overall_weights(profile: TasteProfile) -> tuple[float, float, float]:
    settings = profile.filter_settings
    return normalize_overall_weights(
        settings.overall_weight_alpha,
        settings.overall_weight_beta,
        settings.overall_weight_gamma,
    )


def _community_display_label(
    community_id: str,
    *,
    genre_labels: Mapping[str, str],
    comm_by_id: Mapping[str, Mapping[str, Any]],
) -> str:
    genre_label = genre_labels.get(community_id)
    if genre_label:
        return genre_label
    community = comm_by_id.get(community_id)
    if community is not None:
        centroid = community.get("centroid")
        if centroid:
            return str(centroid)
    return "Stil-Cluster"


def _top_communities_for_review(
    affinity_row: Mapping[str, Any] | None,
    *,
    selected_comms: set[str],
    genre_labels: Mapping[str, str],
    comm_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if affinity_row is None:
        return []
    comms = affinity_row.get("communities")
    if not isinstance(comms, Mapping):
        return []
    entries_any = comms.get("res_10")
    if not isinstance(entries_any, list):
        return []
    entries = [entry for entry in entries_any if isinstance(entry, Mapping)]
    return community_tags_from_entries(
        entries,
        label_for_id=lambda community_id: _community_display_label(
            community_id,
            genre_labels=genre_labels,
            comm_by_id=comm_by_id,
        ),
        selected_community_ids=selected_comms,
    )


def _normalize_archive_row(
    row: Mapping[str, Any],
    *,
    rank: int,
    alpha: float,
    beta: float,
    gamma: float,
) -> dict[str, Any]:
    return {
        "rank": rank,
        "review_id": row.get("review_id"),
        "artist": row.get("artist"),
        "album": row.get("album"),
        "score": row.get("score"),
        "s_a": row.get("s_a"),
        "style_fit_raw": row.get("style_fit_raw"),
        "cosine_fit": row.get("cosine_fit"),
        "rating": row.get("rating"),
        "rating_norm": row.get("rating_norm"),
        "purity_raw": row.get("purity_raw"),
        "breadth_raw": row.get("breadth_raw"),
        "purity_norm": row.get("purity_norm"),
        "breadth_norm": row.get("breadth_norm"),
        "community_spectrum_norm": row.get("community_spectrum_norm"),
        "spectrum_matching_gate": row.get("spectrum_matching_gate"),
        "community_spectrum_effective": row.get("community_spectrum_effective"),
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
        "overall_score": row.get("overall_score"),
        "k_hits": row.get("k_hits"),
        "url": row.get("url"),
        "top_communities": row.get("top_communities") or [],
    }


def _normalize_preference_row(
    row: Mapping[str, Any],
    *,
    rank: int,
    k_hits: int,
    top_communities: list[dict[str, Any]],
) -> dict[str, Any]:
    review = row.get("review")
    if not isinstance(review, Review):
        msg = "preference row must include a Review object"
        raise TypeError(msg)
    return {
        "rank": rank,
        "review_id": row.get("review_id"),
        "artist": review.artist,
        "album": review.album,
        "score": row.get("score"),
        "rating": review.rating,
        "rating_norm": row.get("rating_norm"),
        "purity_raw": row.get("purity_raw"),
        "breadth_raw": row.get("breadth_raw"),
        "purity_norm": row.get("purity_norm"),
        "breadth_norm": row.get("breadth_norm"),
        "community_spectrum_norm": row.get("community_spectrum_norm"),
        "spectrum_matching_gate": row.get("spectrum_matching_gate"),
        "community_spectrum_effective": row.get("community_spectrum_effective"),
        "alpha": row.get("alpha"),
        "beta": row.get("beta"),
        "gamma": row.get("gamma"),
        "overall_score": row.get("overall_score"),
        "k_hits": k_hits,
        "url": review.url,
        "top_communities": top_communities,
    }


SCORE_LAB_DEFAULT_SCORE_MIN = 0.0
SCORE_LAB_DEFAULT_SCORE_MAX = 1.0


def taste_profile_from_saved_document(
    data: Mapping[str, Any],
    *,
    profile_name: str | None = None,
) -> TasteProfile:
    """Build a taste profile from a stored profile document (DB / JSON payload)."""
    selected = data.get("selected_communities")
    if isinstance(selected, list) and selected:
        communities = sorted(str(community_id) for community_id in selected)
    else:
        communities = []
    filter_settings = data.get("filter_settings")
    if not isinstance(filter_settings, dict):
        filter_settings = {}
    weights_raw = data.get("community_weights_raw")
    if not isinstance(weights_raw, dict):
        weights_raw = {}
    name = profile_name or str(data.get("name") or "Profil")
    return TasteProfile.from_mapping(
        {
            "name": name,
            "selected_communities": communities,
            "filter_settings": filter_settings,
            "community_weights_raw": weights_raw,
        },
    )


def load_active_saved_taste_profile(
    active_slug: str | None,
    *,
    profiles_dir: Path | None = None,
) -> TasteProfile | None:
    """Load the signed-in user's saved profile from the database, if available."""
    if not isinstance(active_slug, str) or not active_slug.strip():
        return None
    slug = active_slug.strip()
    try:
        data = load_profile(profiles_dir or default_profiles_dir(), slug)
    except OSError:
        return None
    if data is None:
        return None
    return taste_profile_from_saved_document(data, profile_name=slug)


def lab_slider_settings_from_profile(profile: TasteProfile) -> dict[str, float]:
    """Return Score Lab sidebar slider values derived from a taste profile."""
    settings = profile.filter_settings
    return {
        "overall_weight_alpha": float(settings.overall_weight_alpha),
        "overall_weight_beta": float(settings.overall_weight_beta),
        "overall_weight_gamma": float(settings.overall_weight_gamma),
        "community_spectrum_crossover": float(settings.community_spectrum_crossover),
        "score_min": float(settings.score_min),
        "score_max": float(settings.score_max),
    }


def lab_exploration_slider_defaults(profile: TasteProfile) -> dict[str, float]:
    """Exploration defaults: profile weights, but full S_a interval 0..1."""
    defaults = lab_slider_settings_from_profile(profile)
    defaults["score_min"] = SCORE_LAB_DEFAULT_SCORE_MIN
    defaults["score_max"] = SCORE_LAB_DEFAULT_SCORE_MAX
    return defaults


def profile_for_archive_lab(
    profile: TasteProfile,
    *,
    apply_product_filters: bool,
) -> TasteProfile:
    """Return a profile copy for archive scoring in Score Lab.

    When ``apply_product_filters`` is False, year, rating, and Plattenlabel
    hard filters are relaxed so the lab can show community-scored albums even
    when Empfehlungen filters would exclude everything.
    """
    if apply_product_filters:
        return profile
    relaxed_settings = profile.filter_settings.model_copy(
        update={
            "rating_min": 0.0,
            "rating_max": 10.0,
            "year_min": None,
            "year_max": None,
            "plattenlabel_selection": None,
        },
    )
    return profile.model_copy(update={"filter_settings": relaxed_settings})


def format_score_lab_filter_summary(profile: TasteProfile) -> str:
    """German one-line summary of hard filters on the active profile."""
    settings = profile.filter_settings
    year_lo = settings.year_min if settings.year_min is not None else "Archiv-Min"
    year_hi = settings.year_max if settings.year_max is not None else "Archiv-Max"
    labels = settings.plattenlabel_selection
    label_text = "alle" if labels is None else f"{len(labels)} ausgewählt"
    return (
        f"S_a: {settings.score_min:.2f}-{settings.score_max:.2f}, "
        f"Rating: {settings.rating_min:.0f}-{settings.rating_max:.0f}, "
        f"Jahr: {year_lo}-{year_hi}, Plattenlabel: {label_text}"
    )


def diagnose_score_lab_empty(
    profile: TasteProfile,
    inputs: RecommendationInputs,
    *,
    apply_product_filters: bool,
) -> dict[str, int]:
    """Return candidate counts to explain an empty Score Lab result."""
    selected = selected_communities_from_profile(profile)
    if not selected:
        return {"community_hits": 0, "after_score_range": 0, "after_product_filters": 0}

    score_min = float(profile.filter_settings.score_min)
    score_max = float(profile.filter_settings.score_max)
    aff_map = affinity_by_review_id(inputs.affinities)

    community_hits = 0
    after_score_range = 0
    for obj in inputs.affinities:
        review_id_val = obj.get("review_id")
        if not isinstance(review_id_val, int):
            continue
        affinity_row = aff_map.get(int(review_id_val))
        hits = k_hits_for_review(affinity_row, selected_comms=selected)
        if hits == 0:
            continue
        community_hits += 1
        score, _, _ = _selected_affinity_score_from_row(
            affinity_row,
            selected_comms=selected,
            weights_raw=profile.community_weights_raw,
        )
        if score_min <= score <= score_max:
            after_score_range += 1

    lab_profile = profile_for_archive_lab(
        profile,
        apply_product_filters=apply_product_filters,
    )
    after_product_filters = len(
        RecommendationService(inputs).compute_archive_recommendations(lab_profile),
    )
    return {
        "community_hits": community_hits,
        "after_score_range": after_score_range,
        "after_product_filters": after_product_filters,
    }


def _selected_affinity_score_from_row(
    affinity_row: Mapping[str, Any] | None,
    *,
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
) -> tuple[float, int, float]:
    if affinity_row is None:
        return 0.0, 0, 0.0
    comms = affinity_row.get("communities")
    if not isinstance(comms, Mapping):
        return 0.0, 0, 0.0
    entries_any = comms.get("res_10")
    if not isinstance(entries_any, list):
        return 0.0, 0, 0.0
    score = 0.0
    hits = 0
    max_weighted_value = 0.0
    for entry in entries_any:
        if not isinstance(entry, Mapping):
            continue
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


def _apply_limit(rows: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None or limit <= 0:
        return rows
    return rows[:limit]


def _enrich_rows_with_cosine_fit(
    rows: list[dict[str, Any]],
    *,
    affinities: Sequence[Mapping[str, Any]],
    selected_comms: set[str],
    weights_raw: Mapping[str, float],
) -> None:
    """Attach ``cosine_fit`` to each row from album affinity vectors."""
    aff_map = affinity_by_review_id(affinities)
    for row in rows:
        review_id = row.get("review_id")
        if not isinstance(review_id, int):
            row["cosine_fit"] = 0.0
            continue
        row["cosine_fit"] = cosine_fit_from_affinity_row(
            aff_map.get(review_id),
            selected_comms=selected_comms,
            weights_raw=weights_raw,
        )


def build_score_lab_rows(
    profile: TasteProfile,
    inputs: RecommendationInputs,
    *,
    data_source: ScoreLabDataSource = "archive",
    limit: int | None = 200,
    review_ids: frozenset[int] | None = None,
    apply_product_filters: bool = False,
) -> list[dict[str, Any]]:
    """Build ranked score-lab rows for archive filtering or fixed review IDs."""
    selected_comms = selected_communities_from_profile(profile)
    if not selected_comms:
        return []

    if data_source == "review_ids":
        return _build_review_id_rows(
            profile,
            inputs,
            selected_comms=selected_comms,
            review_ids=review_ids or frozenset(),
            limit=limit,
        )

    archive_profile = profile_for_archive_lab(
        profile,
        apply_product_filters=apply_product_filters,
    )
    alpha, beta, gamma = _effective_overall_weights(archive_profile)
    service = RecommendationService(inputs)
    raw_rows = service.compute_archive_recommendations(archive_profile)
    normalized = [
        _normalize_archive_row(
            row,
            rank=index + 1,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
        )
        for index, row in enumerate(raw_rows)
    ]
    if review_ids:
        normalized = [row for row in normalized if row.get("review_id") in review_ids]
        for index, row in enumerate(normalized):
            row["rank"] = index + 1
    _enrich_rows_with_cosine_fit(
        normalized,
        affinities=inputs.affinities,
        selected_comms=selected_comms,
        weights_raw=archive_profile.community_weights_raw,
    )
    return _apply_limit(normalized, limit)


def _build_review_id_rows(
    profile: TasteProfile,
    inputs: RecommendationInputs,
    *,
    selected_comms: set[str],
    review_ids: frozenset[int],
    limit: int | None,
) -> list[dict[str, Any]]:
    if not review_ids:
        return []

    review_index = {int(review.id): review for review in inputs.reviews}
    reviews = [review_index[rid] for rid in sorted(review_ids) if rid in review_index]
    if not reviews:
        return []

    aff_map = affinity_by_review_id(inputs.affinities)
    comm_by_id = {
        str(community.get("id")): community
        for community in inputs.communities
        if community.get("id")
    }
    filter_settings = profile.filter_settings.model_dump()
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))

    ranked = preference_ranked_rows(
        reviews,
        affinity_by_review_id=aff_map,
        memberships=inputs.memberships,
        selected_comms=selected_comms,
        weights_raw=profile.community_weights_raw,
        filter_settings=filter_settings,
        apply_serendipity=False,
    )
    filtered = [
        row for row in ranked if score_min <= float(row.get("score", 0.0)) <= score_max
    ]
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(filtered):
        review_id = int(row["review_id"])
        affinity_row = aff_map.get(review_id)
        normalized.append(
            _normalize_preference_row(
                row,
                rank=index + 1,
                k_hits=k_hits_for_review(affinity_row, selected_comms=selected_comms),
                top_communities=_top_communities_for_review(
                    affinity_row,
                    selected_comms=selected_comms,
                    genre_labels=inputs.genre_labels,
                    comm_by_id=comm_by_id,
                ),
            ),
        )
    _enrich_rows_with_cosine_fit(
        normalized,
        affinities=inputs.affinities,
        selected_comms=selected_comms,
        weights_raw=profile.community_weights_raw,
    )
    return _apply_limit(normalized, limit)
