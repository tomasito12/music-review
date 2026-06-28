"""Step-by-step score breakdown for one album in Score Lab."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from music_review.application.models import TasteProfile
from music_review.application.recommendation_service import (
    RecommendationInputs,
    selected_communities_from_profile,
)
from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION,
    REFERENCE_POSITION_W_MIN,
)
from music_review.dashboard.recommendation_scoring import (
    breadth_raw_from_selected_community_masses,
    effective_plattentests_rating,
    gini_coefficient,
    normalize_coverage_batch,
    purity_max_weighted_share,
    rating_to_unit_interval,
)
from music_review.domain.reference_masses import reference_community_position_masses

WALKTHROUGH_COMMUNITY_COLUMNS: tuple[str, ...] = (
    "community_id",
    "label",
    "profile_weight",
    "album_affinity",
    "weighted_contribution",
)

WALKTHROUGH_BREADTH_COLUMNS: tuple[str, ...] = (
    "community_id",
    "label",
    "reference_mass",
    "profile_weight",
    "weighted_mass",
)

WALKTHROUGH_STEP_COLUMNS: tuple[str, ...] = (
    "step",
    "formula",
    "inputs",
    "value",
)


def _community_label(
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
    return community_id


def _fmt(value: float, *, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def _batch_purity_bounds(
    batch_rows: Sequence[Mapping[str, Any]],
) -> tuple[float, float]:
    values = [float(row.get("purity_raw", 0.0)) for row in batch_rows]
    if not values:
        return 0.0, 1.0
    return min(values), max(values)


def _batch_breadth_rank(
    review_id: int,
    batch_rows: Sequence[Mapping[str, Any]],
) -> tuple[int, int]:
    ordered = sorted(
        batch_rows,
        key=lambda row: float(row.get("breadth_raw", 0.0)),
    )
    ids = [int(row["review_id"]) for row in ordered if row.get("review_id") is not None]
    if review_id not in ids:
        return 0, len(ids)
    return ids.index(review_id) + 1, len(ids)


WALKTHROUGH_PURITY_COLUMNS: tuple[str, ...] = (
    "step",
    "explanation",
    "calculation",
    "value",
)


def _dominant_community_row(
    community_rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Return the community row with the largest positive weighted contribution."""
    candidates = [
        row for row in community_rows if float(row.get("album_affinity", 0.0)) > 0.0
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: float(row.get("weighted_contribution", 0.0)),
    )


WALKTHROUGH_BATCH_PURITY_COLUMNS: tuple[str, ...] = (
    "rank_stilreinheit",
    "artist",
    "album",
    "purity_raw",
    "purity_norm",
    "is_current_album",
)


def _build_batch_purity_rows(
    batch_rows: Sequence[Mapping[str, Any]],
    *,
    review_id: int,
) -> list[dict[str, Any]]:
    """Sort batch candidates by purity_raw (desc) with min-max norms for display."""
    ordered = sorted(
        batch_rows,
        key=lambda row: float(row.get("purity_raw", 0.0)),
        reverse=True,
    )
    raw_values = [float(row.get("purity_raw", 0.0)) for row in ordered]
    norms = normalize_coverage_batch(raw_values)
    rows: list[dict[str, Any]] = []
    for rank, (row, norm) in enumerate(zip(ordered, norms, strict=True), start=1):
        rid = row.get("review_id")
        rows.append(
            {
                "rank_stilreinheit": rank,
                "artist": str(row.get("artist", "")),
                "album": str(row.get("album", "")),
                "purity_raw": float(row.get("purity_raw", 0.0)),
                "purity_norm": float(norm),
                "is_current_album": isinstance(rid, int) and rid == review_id,
            },
        )
    return rows


def _build_purity_norm_detail(
    *,
    purity_raw: float,
    purity_norm: float,
    purity_lo: float,
    purity_hi: float,
    batch_size: int,
    batch_purity_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Explain purity_norm (batch-relative Stilreinheit) with calculation table."""
    calculation_rows: list[dict[str, Any]] = []
    current_rank = 0
    for row in batch_purity_rows:
        if bool(row.get("is_current_album")):
            current_rank = int(row.get("rank_stilreinheit", 0))
            break

    calculation_rows.append(
        {
            "step": "a) Stilreinheit dieses Albums",
            "explanation": "purity_raw aus Schritt 2 (absolut, 0-1)",
            "calculation": "siehe Schritt 2",
            "value": _fmt(purity_raw),
        },
    )
    calculation_rows.append(
        {
            "step": "b) Batch-Grenzen",
            "explanation": (
                f"Minimum und Maximum von purity_raw über "
                f"{batch_size} Kandidaten in der aktuellen Liste"
            ),
            "calculation": f"min={_fmt(purity_lo)}, max={_fmt(purity_hi)}",
            "value": f"[{_fmt(purity_lo)}, {_fmt(purity_hi)}]",
        },
    )

    if batch_size <= 0:
        calculation_rows.append(
            {
                "step": "c) Stilreinheit purity_norm",
                "explanation": "Keine Kandidaten im Batch",
                "calculation": "purity_norm = 0",
                "value": "0.0000",
            },
        )
        interpretation = "Keine Kandidatenliste für die Batch-Normierung vorhanden."
    elif purity_hi <= purity_lo:
        calculation_rows.append(
            {
                "step": "c) Stilreinheit purity_norm",
                "explanation": (
                    "Alle Kandidaten haben dieselbe purity_raw; "
                    "Min-Max-Norm setzt jeden Wert auf 1.0"
                ),
                "calculation": "keine Streuung -> purity_norm = 1.0 für alle",
                "value": _fmt(purity_norm),
            },
        )
        interpretation = (
            "Im aktuellen Batch ist purity_raw überall gleich. "
            "purity_norm wird deshalb nicht zur Unterscheidung genutzt."
        )
    else:
        span = purity_hi - purity_lo
        calculation_rows.append(
            {
                "step": "c) Stilreinheit purity_norm",
                "explanation": (
                    "Relative Position im Batch: 0 = breiteste Verteilung, "
                    "1 = stilreinster Kandidat"
                ),
                "calculation": (
                    f"({_fmt(purity_raw)} - {_fmt(purity_lo)}) / "
                    f"{_fmt(span)} = {_fmt(purity_norm)}"
                ),
                "value": _fmt(purity_norm),
            },
        )
        if current_rank == 1:
            interpretation = (
                f"Stilreinster Kandidat im Batch (Rang 1 von {batch_size} "
                "bei absteigender purity_raw)."
            )
        elif purity_norm >= 0.85:
            interpretation = (
                f"Gehört zu den stilreinsten Kandidaten "
                f"(Rang {current_rank} von {batch_size}, purity_norm "
                f"{_fmt(purity_norm)})."
            )
        elif purity_norm <= 0.15:
            interpretation = (
                f"Gehört zu den breitesten Kandidaten im Batch "
                f"(Rang {current_rank} von {batch_size}, purity_norm "
                f"{_fmt(purity_norm)})."
            )
        else:
            interpretation = (
                f"Mittleres Spektrum im Batch (Rang {current_rank} von "
                f"{batch_size}, purity_norm {_fmt(purity_norm)})."
            )

    return {
        "purity_raw": purity_raw,
        "purity_norm": purity_norm,
        "purity_lo": purity_lo,
        "purity_hi": purity_hi,
        "batch_size": batch_size,
        "rank_stilreinheit": current_rank,
        "calculation_rows": calculation_rows,
        "batch_purity_rows": list(batch_purity_rows),
        "interpretation": interpretation,
        "concept": (
            "Schritt 3 vergleicht die absolute Stilreinheit (purity_raw) mit "
            "allen anderen Alben in der aktuellen Kandidatenliste. "
            "purity_norm ist kein neuer Messwert, sondern eine Skalierung: "
            "Das breiteste Album im Batch wird auf 0 gesetzt, das "
            "stilreinste auf 1. Ändert sich die Kandidatenliste, kann sich "
            "purity_norm für dasselbe Album verschieben."
        ),
    }


def _build_purity_detail(
    community_rows: list[dict[str, Any]],
    *,
    s_a: float,
    max_weighted: float,
    purity_raw: float,
) -> dict[str, Any]:
    """Explain purity_raw (Stilreinheit) with a small calculation table."""
    dominant = _dominant_community_row(community_rows)
    calculation_rows: list[dict[str, Any]] = []

    if dominant is None or s_a <= 0.0:
        calculation_rows.append(
            {
                "step": "Kein positiver Community-Treffer",
                "explanation": (
                    "Ohne Affinität > 0 auf einer gewählten Community "
                    "ist purity_raw = 0."
                ),
                "calculation": "max(Beitrag) / S_a",
                "value": "0.0000",
            },
        )
        interpretation = (
            "Das Album trifft auf keine deiner gewählten Communities mit "
            "positiver Affinität."
        )
    else:
        dom_label = str(dominant.get("label", ""))
        dom_cid = str(dominant.get("community_id", ""))
        dom_weight = float(dominant.get("profile_weight", 0.0))
        dom_affinity = float(dominant.get("album_affinity", 0.0))
        dom_contrib = float(dominant.get("weighted_contribution", 0.0))
        calculation_rows.extend(
            [
                {
                    "step": "a) Stärkster Einzelbeitrag",
                    "explanation": (
                        f"Community mit dem höchsten Gewicht*Affinität: "
                        f"{dom_label} ({dom_cid})"
                    ),
                    "calculation": (
                        f"{_fmt(dom_weight, digits=2)} * "
                        f"{_fmt(dom_affinity)} = {_fmt(dom_contrib)}"
                    ),
                    "value": _fmt(dom_contrib),
                },
                {
                    "step": "b) Gesamt-Stilpassung S_a",
                    "explanation": (
                        "Summe aller Beiträge (Gewicht * Affinität) "
                        "über deine gewählten Communities"
                    ),
                    "calculation": "Summe der Spalte weighted_contribution",
                    "value": _fmt(s_a),
                },
                {
                    "step": "c) Stilreinheit purity_raw",
                    "explanation": (
                        "Wie stark ein einzelner Cluster den Gesamtscore "
                        "dominiert (Anteil des stärksten Beitrags an S_a)"
                    ),
                    "calculation": (
                        f"{_fmt(dom_contrib)} / {_fmt(s_a)} = {_fmt(purity_raw)}"
                    ),
                    "value": _fmt(purity_raw),
                },
            ],
        )
        if purity_raw >= 0.85:
            interpretation = (
                f"Stilreines Album: Der Treffer auf „{dom_label}“ macht "
                f"{_fmt(100.0 * purity_raw, digits=1)} % von S_a aus."
            )
        elif purity_raw >= 0.55:
            interpretation = (
                f"Ein Cluster ({dom_label}) dominiert, aber andere Communities "
                "tragen spürbar bei."
            )
        else:
            interpretation = (
                "Breites Spektrum: Viele Communities tragen vergleichbar viel "
                "zu S_a bei (typisch für Crossover-Alben)."
            )

    return {
        "purity_raw": purity_raw,
        "s_a": s_a,
        "max_weighted_contribution": max_weighted,
        "dominant_community_id": (
            None if dominant is None else str(dominant.get("community_id"))
        ),
        "dominant_label": None if dominant is None else str(dominant.get("label")),
        "calculation_rows": calculation_rows,
        "interpretation": interpretation,
        "concept": (
            "Stilreinheit misst nicht die absolute Passung, sondern die "
            "Konzentration: Wenn fast die ganze Stilpassung S_a aus einem "
            "einzigen Community-Treffer kommt, ist purity_raw nahe 1. Wenn "
            "viele Communities gleich stark beitragen, sinkt purity_raw."
        ),
    }


def build_album_score_walkthrough(
    row: Mapping[str, Any],
    profile: TasteProfile,
    inputs: RecommendationInputs,
    *,
    batch_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return tables and formulas that explain one album's overall score."""
    review_id = row.get("review_id")
    if not isinstance(review_id, int):
        msg = "row must include integer review_id"
        raise TypeError(msg)

    review_index = {int(review.id): review for review in inputs.reviews}
    review = review_index.get(review_id)
    if review is None:
        msg = f"review_id {review_id} not found in corpus"
        raise ValueError(msg)

    selected = selected_communities_from_profile(profile)
    weights_raw = profile.community_weights_raw
    comm_by_id = {
        str(community.get("id")): community
        for community in inputs.communities
        if community.get("id")
    }
    aff_map = {
        int(obj["review_id"]): obj
        for obj in inputs.affinities
        if isinstance(obj.get("review_id"), int)
    }
    affinity_row = aff_map.get(review_id)
    affinity_by_cid: dict[str, float] = {}
    if affinity_row is not None:
        comms = affinity_row.get("communities")
        if isinstance(comms, Mapping):
            entries_any = comms.get("res_10")
            if isinstance(entries_any, list):
                for entry in entries_any:
                    if not isinstance(entry, Mapping):
                        continue
                    cid = str(entry.get("id"))
                    score_val = entry.get("score")
                    if isinstance(score_val, (int, float)):
                        affinity_by_cid[cid] = float(score_val)

    community_rows: list[dict[str, Any]] = []
    s_a = 0.0
    max_weighted = 0.0
    max_cid: str | None = None
    for cid in sorted(selected):
        affinity = float(affinity_by_cid.get(cid, 0.0))
        weight = float(
            weights_raw.get(cid, RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW),
        )
        contribution = weight * affinity
        s_a += contribution
        if affinity > 0 and contribution >= max_weighted:
            max_weighted = contribution
            max_cid = cid
        community_rows.append(
            {
                "community_id": cid,
                "label": _community_label(
                    cid,
                    genre_labels=inputs.genre_labels,
                    comm_by_id=comm_by_id,
                ),
                "profile_weight": weight,
                "album_affinity": affinity,
                "weighted_contribution": contribution,
            },
        )
    for item in community_rows:
        contrib = float(item["weighted_contribution"])
        item["share_of_s_a"] = contrib / s_a if s_a > 0 else 0.0
        item["is_dominant"] = (
            s_a > 0
            and max_cid is not None
            and item["community_id"] == max_cid
            and float(item["album_affinity"]) > 0
        )

    purity_raw = float(
        row.get("purity_raw", purity_max_weighted_share(max_weighted, s_a)),
    )
    purity_detail = _build_purity_detail(
        community_rows,
        s_a=s_a,
        max_weighted=max_weighted,
        purity_raw=purity_raw,
    )
    ref_masses = reference_community_position_masses(
        review,
        inputs.memberships,
        res_key="res_10",
        w_min=REFERENCE_POSITION_W_MIN,
    )
    breadth_rows: list[dict[str, Any]] = []
    weighted_masses: list[float] = []
    for cid in sorted(selected):
        ref_mass = float(ref_masses.get(cid, 0.0))
        weight = float(
            weights_raw.get(cid, RECOMMENDATION_DEFAULT_COMMUNITY_WEIGHT_RAW),
        )
        weighted_mass = weight * ref_mass
        weighted_masses.append(weighted_mass)
        breadth_rows.append(
            {
                "community_id": cid,
                "label": _community_label(
                    cid,
                    genre_labels=inputs.genre_labels,
                    comm_by_id=comm_by_id,
                ),
                "reference_mass": ref_mass,
                "profile_weight": weight,
                "weighted_mass": weighted_mass,
            },
        )
    gini = gini_coefficient(weighted_masses)
    breadth_raw = float(
        row.get(
            "breadth_raw",
            breadth_raw_from_selected_community_masses(
                ref_masses,
                selected,
                weights_raw,
            ),
        ),
    )

    rating_raw = review.rating
    rating_effective = effective_plattentests_rating(
        rating_raw,
        default_when_missing=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    )
    rating_norm = float(
        row.get(
            "rating_norm",
            rating_to_unit_interval(
                rating_raw,
                default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
            ),
        ),
    )
    crossover = float(profile.filter_settings.community_spectrum_crossover)
    purity_norm = float(row.get("purity_norm", 0.0))
    breadth_norm = float(row.get("breadth_norm", 0.0))
    spectrum_norm = float(row.get("community_spectrum_norm", 0.0))
    gate = float(row.get("spectrum_matching_gate", 0.0))
    spectrum_eff = float(row.get("community_spectrum_effective", 0.0))
    alpha = float(row.get("alpha", 0.0))
    beta = float(row.get("beta", 0.0))
    gamma = float(row.get("gamma", 0.0))
    overall = float(row.get("overall_score", 0.0))

    purity_lo, purity_hi = _batch_purity_bounds(batch_rows)
    batch_purity_rows = _build_batch_purity_rows(batch_rows, review_id=review_id)
    purity_norm_detail = _build_purity_norm_detail(
        purity_raw=purity_raw,
        purity_norm=purity_norm,
        purity_lo=purity_lo,
        purity_hi=purity_hi,
        batch_size=len(batch_rows),
        batch_purity_rows=batch_purity_rows,
    )
    breadth_rank, breadth_n = _batch_breadth_rank(review_id, batch_rows)
    gate_k = RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION

    term_alpha = alpha * s_a
    term_beta = beta * rating_norm
    term_gamma = gamma * spectrum_eff

    style_steps: list[dict[str, Any]] = [
        {
            "step": "1. Gewichtete Community-Treffer",
            "formula": "S_a = Summe(profile_weight * album_affinity)",
            "inputs": f"{len(selected)} Communities, siehe Tabelle unten",
            "value": _fmt(s_a),
        },
        {
            "step": "2. Stilreinheit (roh)",
            "formula": "purity_raw = stärkster_Einzelbeitrag / S_a",
            "inputs": (
                f"stärkster={_fmt(max_weighted)}, S_a={_fmt(s_a)}"
                if s_a > 0
                else "S_a=0"
            ),
            "value": _fmt(purity_raw),
        },
    ]

    spectrum_steps: list[dict[str, Any]] = [
        {
            "step": "3. Stilreinheit (normiert)",
            "formula": "purity_norm = (purity_raw - min) / (max - min), Batch",
            "inputs": (
                f"min={_fmt(purity_lo)}, max={_fmt(purity_hi)}, n={len(batch_rows)}"
            ),
            "value": _fmt(purity_norm),
        },
        {
            "step": "4. Abdeckungsbreite (roh)",
            "formula": "breadth_raw = 1 - Gini(weighted reference masses)",
            "inputs": f"Gini={_fmt(gini)}, Referenz-Künstler siehe Tabelle",
            "value": _fmt(breadth_raw),
        },
        {
            "step": "5. Abdeckungsbreite (normiert)",
            "formula": "breadth_norm = Perzentil-Rang in Kandidatenliste",
            "inputs": f"Rang {breadth_rank} von {breadth_n}",
            "value": _fmt(breadth_norm),
        },
        {
            "step": "6. Spectrum-Mix",
            "formula": ("(1-lambda)*purity_norm + lambda*breadth_norm"),
            "inputs": (
                f"lambda={_fmt(crossover, digits=2)}, "
                f"purity_norm={_fmt(purity_norm)}, "
                f"breadth_norm={_fmt(breadth_norm)}"
            ),
            "value": _fmt(spectrum_norm),
        },
        {
            "step": "7. Passungs-Gate",
            "formula": f"g(S_a) = S_a / (S_a + {_fmt(gate_k, digits=2)})",
            "inputs": f"S_a={_fmt(s_a)}",
            "value": _fmt(gate),
        },
        {
            "step": "8. Spectrum effektiv",
            "formula": "community_spectrum_effective = spectrum_norm * g(S_a)",
            "inputs": (f"spectrum_norm={_fmt(spectrum_norm)}, gate={_fmt(gate)}"),
            "value": _fmt(spectrum_eff),
        },
    ]

    overall_steps: list[dict[str, Any]] = [
        {
            "step": "A. Stilpassung",
            "formula": "alpha * S_a",
            "inputs": f"alpha={_fmt(alpha, digits=2)}, S_a={_fmt(s_a)}",
            "value": _fmt(term_alpha),
        },
        {
            "step": "B. Rating",
            "formula": "beta * rating_norm",
            "inputs": (
                f"beta={_fmt(beta, digits=2)}, "
                f"rating={rating_raw if rating_raw is not None else 'fehlend'}"
                f" -> {_fmt(rating_effective, digits=1)}/10 "
                f"-> rating_norm={_fmt(rating_norm)}"
            ),
            "value": _fmt(term_beta),
        },
        {
            "step": "C. Spectrum",
            "formula": "gamma * community_spectrum_effective",
            "inputs": (
                f"gamma={_fmt(gamma, digits=2)}, spectrum_eff={_fmt(spectrum_eff)}"
            ),
            "value": _fmt(term_gamma),
        },
        {
            "step": "Gesamt overall_score",
            "formula": "alpha*S_a + beta*rating_norm + gamma*spectrum_eff",
            "inputs": (f"{_fmt(term_alpha)} + {_fmt(term_beta)} + {_fmt(term_gamma)}"),
            "value": _fmt(overall),
        },
    ]

    return {
        "review_id": review_id,
        "artist": row.get("artist", review.artist),
        "album": row.get("album", review.album),
        "url": row.get("url", review.url),
        "rank": row.get("rank"),
        "community_rows": community_rows,
        "purity_detail": purity_detail,
        "purity_norm_detail": purity_norm_detail,
        "breadth_rows": breadth_rows,
        "style_steps": style_steps,
        "spectrum_steps": spectrum_steps,
        "overall_steps": overall_steps,
        "summary": {
            "s_a": s_a,
            "overall_score": overall,
            "batch_size": len(batch_rows),
        },
    }
