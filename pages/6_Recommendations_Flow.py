from __future__ import annotations

import html
import random
from pathlib import Path
from typing import Any

import streamlit as st
from pages.page_helpers import (
    format_release_date,
    get_selected_communities,
    load_communities_res_10,
    load_community_memberships,
    load_genre_labels_res_10,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION,
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
from music_review.dashboard.user_profile_store import ACTIVE_PROFILE_SESSION_KEY
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.pipeline.retrieval.reference_graph import (
    reference_community_position_masses,
)
from music_review.pipeline.retrieval.vector_store import (
    CHUNK_COLLECTION_NAME,
    search_reviews_with_variants,
)

# Streamlit widget keys: keep centralized to avoid accidental duplicates.
KEY_CHAT_RESET_BUTTON = "rec_chat_reset_button"
KEY_CHAT_INPUT = "rec_chat_input"
KEY_RAG_MAX_DISTANCE = "rec_rag_max_distance"
KEY_FILTER_ADJUST_BUTTON = "rec_filter_adjust_button"
KEY_START_WORKFLOW_BUTTON = "rec_start_workflow_button"
KEY_CHAT_MESSAGES = "rec_chat_messages"

# Freitext-RAG: max. reviews after fusion (N). Top-k per variant must be large
# enough that fusion can reach N (chunk overlap + strategy A = single variant).
RAG_FUSION_N_RESULTS = 2500
RAG_TOP_K_PER_VARIANT = 2500


def _recommendations_css() -> None:
    st.markdown(
        """
        <style>
        .rec-page-title {
            font-size: 1.6rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        .rec-page-desc { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.3rem; }
        .rec-card {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .rec-card:hover {
            border-color: #d1d5db;
            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.06);
        }
        .rec-card-rag {
            border: 1px solid #6366f1;
            background: #eef2ff;
        }
        .rec-header {
            margin-bottom: 0.35rem;
            display: flex;
            align-items: baseline;
            gap: 0.35rem;
            flex-wrap: wrap;
        }
        .rec-title {
            font-size: 1.05rem;
            font-weight: 600;
            text-decoration: none;
            color: #111827;
        }
        .rec-title:hover { text-decoration: underline; color: #1d4ed8; }
        .rec-meta {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 0.40rem;
        }
        .rec-meta-formula {
            font-size: 0.76rem;
            color: #64748b;
            margin: 0.15rem 0 0.35rem 0;
            line-height: 1.35;
            font-variant-numeric: tabular-nums;
        }
        .rec-communities {
            font-size: 0.78rem;
            color: #4b5563;
            margin-bottom: 0.35rem;
        }
        .rec-comm-tag {
            display: inline-flex;
            align-items: center;
            padding: 0.10rem 0.45rem;
            margin: 0 0.25rem 0.25rem 0;
            border-radius: 999px;
            border: 1px solid transparent;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .rec-excerpt {
            font-size: 0.86rem;
            line-height: 1.5;
            color: #4b5563;
        }
        .rec-rank {
            font-variant-numeric: tabular-nums;
            color: #9ca3af;
            font-size: 0.85rem;
            margin-right: 0.75rem;
        }
        /* Two-pane layout: filter vs. semantic / chat */
        .rec-pane-header {
            margin: -0.15rem 0 0.85rem 0;
            padding: 0.2rem 0 0.85rem 0.85rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.4);
        }
        .rec-pane-header-filter {
            border-left: 3px solid #64748b;
        }
        .rec-pane-header-semantic {
            border-left: 3px solid #6366f1;
            border-bottom-color: rgba(129, 140, 248, 0.35);
        }
        .rec-eyebrow {
            font-size: 0.65rem;
            font-weight: 650;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 0.28rem;
        }
        .rec-pane-header-semantic .rec-eyebrow { color: #818cf8; }
        .rec-pane-title {
            font-size: 1.02rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #0f172a;
            line-height: 1.3;
        }
        .rec-pane-sub {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 0.45rem;
            line-height: 1.45;
            max-width: 36rem;
        }
        .rec-results-divider {
            margin: 1rem 0 0.65rem 0;
            padding-top: 0.85rem;
            border-top: 1px dashed rgba(100, 116, 139, 0.35);
        }
        .rec-results-label {
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #818cf8;
            margin-bottom: 0.35rem;
        }
        .rec-results-title {
            font-size: 0.92rem;
            font-weight: 600;
            color: #312e81;
            letter-spacing: -0.01em;
        }
        .rec-callout {
            font-size: 0.84rem;
            color: #475569;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            line-height: 1.5;
            margin: 0.35rem 0 0.5rem 0;
        }
        .rec-callout-warn {
            background: #fffbeb;
            border-color: #fde68a;
            color: #92400e;
        }
        .rec-callout-info {
            background: #eff6ff;
            border-color: #bfdbfe;
            color: #1e40af;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600)
def _load_reviews_and_metadata() -> tuple[list[Any], dict[int, dict[str, Any]]]:
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
def _load_affinities() -> list[dict[str, Any]]:
    path = resolve_data_path("data/album_community_affinities.jsonl")
    p = Path(path)
    if not p.exists():
        return []
    records: list[dict[str, Any]] = []
    for obj in iter_jsonl_objects(p, log_errors=False):
        if isinstance(obj, dict) and "review_id" in obj and "communities" in obj:
            records.append(obj)
    return records


@st.cache_data(ttl=3600)
def _search_rag_hits(
    query_text: str,
    *,
    strategy: str = "B",
    n_results: int = RAG_FUSION_N_RESULTS,
    top_k_per_variant: int = RAG_TOP_K_PER_VARIANT,
) -> list[dict[str, Any]]:
    """Run Chroma semantic search for the free-text query."""
    return search_reviews_with_variants(
        query_text,
        strategy=strategy,
        n_results=n_results,
        top_k_per_variant=top_k_per_variant,
        where=None,
        collection_name=CHUNK_COLLECTION_NAME,
    )


def _compute_recommendations() -> list[dict[str, Any]]:
    selected_comms = get_selected_communities()
    if not selected_comms:
        return []

    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}

    year_min = int(filter_settings.get("year_min", 1990))
    year_max = int(filter_settings.get("year_max", 2030))
    rating_min = float(filter_settings.get("rating_min", 0.0))
    rating_max = float(filter_settings.get("rating_max", 10.0))
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))
    sort_mode = str(filter_settings.get("sort_mode", "Deterministisch"))
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

    reviews, metadata = _load_reviews_and_metadata()
    affinities = _load_affinities()
    memberships = load_community_memberships()
    communities = load_communities_res_10()
    genre_labels = load_genre_labels_res_10()

    if not reviews or not affinities:
        return []

    review_index: dict[int, Any] = {int(r.id): r for r in reviews}
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

        # Top-Communities nach Affinität (unabhängig von Auswahl), für Anzeige
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

        # Score nur über ausgewählte Communities; max Einzelbeitrag für Reinheit
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
            w = float(weights_raw.get(cid, 1.0))
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
        label_list = meta.get("labels") or []
        if not isinstance(label_list, list):
            label_list = []
        label_str = ", ".join(str(label) for label in label_list)

        # Aufbereitete Top-Community-Infos für die Darstellung
        top_communities: list[dict[str, Any]] = []
        for e in top_entries:
            cid = str(e.get("id"))
            aff = float(e.get("score", 0.0))
            label = genre_labels.get(cid)
            c_obj = comm_by_id.get(cid)
            if not label and isinstance(c_obj, dict):
                centroid = c_obj.get("centroid")
                if centroid:
                    label = str(centroid)
            if not label:
                label = f"Community {cid}"
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

    # Immer zuerst nach echtem Gesamtscore; Serendipity mischt die Reihenfolge
    # (Spearman-Rangkorrelation vor/nachher grob ~ 1 - s).
    candidates.sort(key=lambda x: float(x["overall_score"]), reverse=True)
    if sort_mode == "Serendipity" and serendipity > 0.0:
        # Kein fester Seed: bei jedem Neuaufbau der Liste frische Zufallswerte.
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


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Empfehlungen",
        page_icon="🎵",
        layout="wide",
    )

    _recommendations_css()

    st.markdown(
        '<p class="rec-page-title">Deine Empfehlungen</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="rec-page-desc">Basierend auf deinen gewählten Communities, '
        "Filtereinstellungen und (optional) deiner Stimmungsbeschreibung.</p>",
        unsafe_allow_html=True,
    )

    recs = _compute_recommendations()

    if not recs:
        st.warning(
            "Es konnten keine passenden Alben auf Basis der aktuellen Auswahl "
            "und Filter gefunden werden. Du kannst die Filter zurücknehmen oder "
            "andere Communities wählen.",
        )
        if st.button("Zurück zu den Filtern"):
            st.switch_page("pages/5_Filter_Flow.py")
        return

    # Kurze, nachvollziehbare Erklärung der aktuellen Score-Berechnung
    selected_comms = get_selected_communities()
    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}

    year_min = int(filter_settings.get("year_min", 1990))
    year_max = int(filter_settings.get("year_max", 2030))
    rating_min = float(filter_settings.get("rating_min", 0.0))
    rating_max = float(filter_settings.get("rating_max", 10.0))
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))
    sort_mode = str(filter_settings.get("sort_mode", "Deterministisch"))
    serendipity = float(filter_settings.get("serendipity", 0.0))
    crossover_ui = float(
        filter_settings.get(
            "community_spectrum_crossover",
            RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
        )
    )
    fs_for_weights = st.session_state.get("filter_settings") or {}
    wa = fs_for_weights.get("overall_weight_alpha")
    wb = fs_for_weights.get("overall_weight_beta")
    wc = fs_for_weights.get("overall_weight_gamma")
    if wa is not None and wb is not None and wc is not None:
        oa, ob, og = normalize_overall_weights(float(wa), float(wb), float(wc))
    else:
        oa, ob, og = get_recommendation_overall_weights()

    with st.expander("Wie werden die Scores berechnet?", expanded=True):
        st.markdown(
            "- **`S_a` (Community-Affinität)**:\n"
            "  `S_a = Summe (Gewicht_c * Affinitaet_c,Album)` ueber gewählte "
            "Communities\n"
            "  (Affinitäten aus `album_community_affinities.jsonl`, `res_10`).\n"
            "- **`rating_norm`**: Plattentests-Rating / 10 (0 bis 1). "
            f"Ohne Rating: **{RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING:.0f}/10** "
            "angenommen.\n"
            "- **Reinheit** `purity_raw`: Anteil von `S_a`, der auf die "
            "**eine** stärkste gewählte Community entfällt (hoch = blütenrein).\n"
            "- **Breite** `breadth_raw`: **1 - Gini** ueber positionsgewichtete "
            "Referenzmasse je **gewaehlter** Community (wie bei Affinitaets-Pipeline: "
            f"`position_weight`, `w_min={REFERENCE_POSITION_W_MIN}`). "
            "Referenzen ausserhalb der Auswahl zaehlen nicht. Gleichverteilung der "
            "Masse -> `breadth_raw` nahe 1; eine Community dominiert -> nahe 0.\n"
            f"- **Regler lambda (aktuell {crossover_ui:.2f})**: `purity_norm` ist "
            "min-max ueber die Trefferliste. `breadth_norm` ist **Perzentil-Rang** "
            "nach `breadth_raw`: Album mit **geringster** Breite in der Liste -> 0, "
            "**groesster** Breite -> 1. Dann "
            "`community_spectrum_norm = (1-lambda)*purity_norm + lambda*breadth_norm`. "
            "**lambda=0** bevorzugt **bluetenreine** Alben; **lambda=1** bevorzugt "
            "**Cross-Over** (relativ zur aktuellen Liste).\n"
            f"- **Matching-Kopplung (probeweise)**: Der Spektrum-Term wird mit "
            f"`g(S_a) = S_a / (S_a + k)` multipliziert, aktuell `k = "
            f"{RECOMMENDATION_SPECTRUM_MATCHING_GATE_HALF_SATURATION:g}` "
            f"(bei `S_a = k` ist `g = 0.5`). "
            "`effektives_Spektrum = community_spectrum_norm * g(S_a)`. "
            "`k <= 0` in der Config schaltet die Kopplung aus (`g = 1`).\n"
            "- **Gesamtscore** (alpha, beta, gamma aus den Filtern, vorher auf Summe 1 "
            "normiert):\n"
            f"  `overall = {oa:.2f}*S_a + {ob:.2f}*rating_norm + "
            f"{og:.2f}*effektives_Spektrum`\n"
            "  **gamma** (normiert) steuert dabei den Anteil des "
            "Community-Spektrums vs. S_a und Rating.\n"
            "- **Sortierung**: absteigend nach `overall`. **Serendipity** (Slider "
            "``s``): zuerst dieselbe Reihenfolge, dann wird mit "
            "``(1-s) * Rang_norm + s * Zufall`` neu sortiert (aufsteigend). "
            "``s=0`` unverändert; ``s=1`` fast vollständig zufällige Permutation; "
            "dazwischen ist die **Spearman-Korrelation** der Plätze vor/nachher "
            "in etwa **1 - s** (intuitiv: Rest bleibt am Ranking haengen).\n",
        )

        if selected_comms:
            # Normierte Gewichte nur zur Anzeige.
            # Score-Berechnung bleibt bei Roh-Gewichten.
            total_w = sum(float(weights_raw.get(cid, 1.0)) for cid in selected_comms)
            if total_w <= 0:
                n = len(selected_comms)
                norm = {cid: 1.0 / n for cid in selected_comms}
            else:
                norm = {
                    cid: float(weights_raw.get(cid, 1.0)) / total_w
                    for cid in selected_comms
                }

            weights_lines = []
            for cid in sorted(selected_comms):
                w_raw = float(weights_raw.get(cid, 1.0))
                w_norm = norm[cid]
                weights_lines.append(
                    f"- Community **{cid}**: Roh-Gewicht **{w_raw:.2f}**, "
                    f"normiert **{w_norm:.3f}**",
                )
            st.markdown("**Aktuelle Gewichte (normiert für Erklärung):**")
            st.markdown("\n".join(weights_lines))
        else:
            st.markdown(
                "**Aktuelle Gewichte:** Noch keine Communities gewählt "
                "(Score-Berechnung deaktiviert).",
            )

        ph = RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING
        st.markdown(
            "**Zusätzliche Filter, bevor ein Album angezeigt wird:**\n"
            f"- Veröffentlichungsjahr: **{year_min}-{year_max}**\n"
            f"- Rating (effektiv; fehlend = **{ph:.0f}/10**): "
            f"**{rating_min:.1f}-{rating_max:.1f}**\n"
            f"- Score-Range (`S_a`): **{score_min:.2f}-{score_max:.2f}**\n"
            f"- Bluetenrein <-> Cross-Over (lambda): **{crossover_ui:.2f}**\n"
            f"- Gesamtscore-Gewichte (normiert): alpha={oa:.3f}, beta={ob:.3f}, "
            f"gamma={og:.3f}\n"
            f"- Sortierung: **{sort_mode}**"
            + (f" (Serendipity={serendipity})" if sort_mode == "Serendipity" else ""),
        )

    st.markdown(f"**{len(recs)} Alben entsprechen aktuell deinen Kriterien.**")

    col_left, col_right = st.columns([2, 1], gap="large")

    # Right: single panel (chat + RAG tuning + results slot). Placeholder keeps
    # results in this column after the left pane and RAG computation run.
    with col_right, st.container(border=True):
        st.markdown(
            '<div class="rec-pane-header rec-pane-header-semantic">'
            '<div class="rec-eyebrow">Semantische Suche</div>'
            '<div class="rec-pane-title">Feintuning im Dialog</div>'
            '<div class="rec-pane-sub">Beschreibe Stimmung, Klang oder '
            "Inhalte. Unten siehst du die Alben, die semantisch am besten "
            "passen - unabhaengig von der linken Rangliste.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        chat_reset = st.button("Chat zurücksetzen", key=KEY_CHAT_RESET_BUTTON)
        if chat_reset:
            st.session_state["free_text_query"] = ""
            st.session_state[KEY_CHAT_MESSAGES] = []

        chat_messages = st.session_state.get(KEY_CHAT_MESSAGES)
        if not isinstance(chat_messages, list):
            chat_messages = []
        if not chat_messages:
            chat_messages = [
                {
                    "role": "assistant",
                    "content": (
                        "Kannst du mir beschreiben, nach welcher Musik du "
                        "gerade suchst?"
                    ),
                }
            ]

        # Process chat_input *before* rendering messages: Streamlit runs the script
        # only once per send; rendering first would skip the new user bubble until
        # another interaction. (chat_input stays visually at the bottom of the app.)
        chat_input = st.chat_input(
            "Stimmung oder Inhalte beschreiben …",
            key=KEY_CHAT_INPUT,
        )
        if chat_input is not None:
            chat_input_clean = chat_input.strip()
            st.session_state["free_text_query"] = chat_input_clean
            if chat_input_clean:
                chat_messages.append({"role": "user", "content": chat_input_clean})
                assistant_reply = (
                    "Alles klar - ich passe die Trefferliste an deine Beschreibung an."
                )
                chat_messages.append(
                    {"role": "assistant", "content": assistant_reply},
                )
        st.session_state[KEY_CHAT_MESSAGES] = chat_messages

        for msg in chat_messages:
            role = msg.get("role")
            content = msg.get("content")
            if role not in {"assistant", "user"}:
                continue
            if not isinstance(content, str):
                continue
            with st.chat_message(role):
                st.markdown(content)

        q_show = (st.session_state.get("free_text_query") or "").strip()
        if q_show:
            st.caption(f"**Aktuelle Freitext-Suche:** {q_show}")

        free_text = (st.session_state.get("free_text_query") or "").strip()

        rag_max_distance_ui = st.slider(
            "Max. Distanz (Freitext-Ähnlichkeit, niedriger = ähnlicher)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.05,
            disabled=not bool(free_text),
            key=KEY_RAG_MAX_DISTANCE,
        )
        results_placeholder = st.empty()

    # --- RAG-Abgleich (Freitext) ---
    free_text = (st.session_state.get("free_text_query") or "").strip()
    max_distance = float(rag_max_distance_ui) if free_text else None
    rag_hits_by_id: dict[int, dict[str, Any]] = {}
    rag_allowed_ids: set[int] = set()
    rag_strategy = str(
        (st.session_state.get("filter_settings") or {}).get("rag_query_strategy", "B"),
    ).upper()
    if rag_strategy not in {"A", "B", "C"}:
        rag_strategy = "B"

    if free_text:
        try:
            rag_hits = _search_rag_hits(
                free_text,
                strategy=rag_strategy,
            )
        except RuntimeError as e:
            if "OPENAI_API_KEY" in str(e):
                st.error(
                    "OpenAI API key not set. "
                    "Set `OPENAI_API_KEY` in your environment or .env."
                )
            else:
                st.error(f"RAG search failed: {e}")
            rag_hits = []
        except Exception as e:
            st.error(f"RAG search failed: {e}")
            rag_hits = []

        # Speichern: id -> hit, und allowed set via distance threshold
        for h in rag_hits:
            rid_val = h.get("review_id")
            rid: int | None
            if isinstance(rid_val, int):
                rid = rid_val
            else:
                try:
                    rid = int(rid_val) if rid_val is not None else None
                except (TypeError, ValueError):
                    rid = None
            if rid is None:
                continue
            dist = h.get("distance")
            if isinstance(dist, (int, float)):
                # Keep the best (smallest distance) chunk hit per review_id.
                prev = rag_hits_by_id.get(rid)
                prev_dist = prev.get("distance") if isinstance(prev, dict) else None
                if (
                    prev is None
                    or not isinstance(prev_dist, (int, float))
                    or float(dist) < float(prev_dist)
                ):
                    rag_hits_by_id[rid] = h

                if float(dist) <= float(max_distance):
                    rag_allowed_ids.add(rid)

    # Kachel-Darstellung (Filtertreffer; ggf. mit Freitext-Hervorhebung)
    def _render_filter_cards(
        rec_list: list[dict[str, Any]],
        *,
        rag_match: set[int],
        rank_start: int = 1,
    ) -> None:
        num_cols = 1
        cols = st.columns(num_cols)
        for idx, rec in enumerate(rec_list):
            rank = rank_start + idx
            col = cols[idx % num_cols]
            with col:
                artist = rec.get("artist") or ""
                album = rec.get("album") or ""
                url = rec.get("url") or ""
                rating = rec.get("rating")
                year = rec.get("year")
                labels = rec.get("labels") or ""
                score = float(rec.get("score") or 0.0)
                overall = float(rec.get("overall_score") or 0.0)
                spec_raw = float(rec.get("community_spectrum_norm") or 0.0)
                spec_eff = float(
                    rec.get("community_spectrum_effective", spec_raw) or 0.0,
                )
                spec_gate = float(rec.get("spectrum_matching_gate", 1.0) or 1.0)
                top_comms = rec.get("top_communities") or []
                rag_distance = None
                hit: dict[str, Any] | None = None
                if rec.get("review_id") in rag_match:
                    hit = rag_hits_by_id.get(int(rec["review_id"]))
                    if hit and isinstance(hit.get("distance"), (int, float)):
                        rag_distance = float(hit["distance"])

                is_rag = rag_distance is not None

                snippet_source = rec.get("text") or ""
                if is_rag and hit:
                    snippet_source = (
                        hit.get("chunk_text") or hit.get("text") or snippet_source
                    )
                snippet = snippet_source[:260] + (
                    "…" if len(snippet_source) > 260 else ""
                )

                header = f"{html.escape(str(artist))} — {html.escape(str(album))}"
                if url:
                    link_attrs = (
                        f'href="{html.escape(url)}" target="_blank" rel="noopener"'
                    )
                    header_html = f'<a {link_attrs} class="rec-title">{header}</a>'
                else:
                    header_html = f'<span class="rec-title">{header}</span>'
                rank_html = (
                    f'<span class="rec-rank" aria-label="Platz {rank}">{rank}.</span>'
                )

                release_str = format_release_date(rec.get("release_date"), year)
                if rating is not None:
                    rating_bit = f"Rating: {float(rating):g}/10"
                else:
                    rating_bit = (
                        f"Rating: {RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING:.0f}/10 "
                        "(angenommen)"
                    )
                core = (
                    f"{release_str + ' - ' if release_str else ''}"
                    f"{labels + ' - ' if labels else ''}"
                    f"{rating_bit} - Gesamt: {overall:.3f} "
                    f"(Matching-Score: {score:.3f}, "
                    f"Abdeckungsquantil eff.: {spec_eff:.3f} "
                    f"[roh {spec_raw:.3f} * g(S_a)={spec_gate:.3f}])"
                )
                if is_rag and rag_distance is not None:
                    core += f" - Freitext-Distanz: {rag_distance:.3f}"
                meta_html = html.escape(core)

                snippet_html = html.escape(snippet).replace("\n", "<br>")

                card_class = "rec-card rec-card-rag" if is_rag else "rec-card"
                card = f'<div class="{card_class}">'
                card += f'<div class="rec-header">{rank_html}{header_html}</div>'
                if meta_html:
                    card += f'<div class="rec-meta">{meta_html}</div>'
                if top_comms:
                    card += '<div class="rec-communities">'
                    for tc in top_comms:
                        label = str(tc.get("label") or "")
                        aff = float(tc.get("affinity") or 0.0)
                        if aff >= 0.6:
                            bg = "#0f766e"
                            border = "#0f766e"
                            fg = "#ecfeff"
                            bars = "▮▮▮"
                        elif aff >= 0.3:
                            bg = "#22c55e"
                            border = "#16a34a"
                            fg = "#ecfdf3"
                            bars = "▮▮"
                        elif aff >= 0.1:
                            bg = "#e0f2fe"
                            border = "#93c5fd"
                            fg = "#0f172a"
                            bars = "▮"
                        else:
                            bg = "#f3f4f6"
                            border = "#e5e7eb"
                            fg = "#4b5563"
                            bars = ""

                        tag_text = f"{label}"
                        if bars:
                            tag_text += f" {bars}"
                        card += (
                            f'<span class="rec-comm-tag" '
                            f'style="background-color:{bg};border-color:{border};'
                            f'color:{fg};">'
                            f"{html.escape(tag_text)}"
                            "</span>"
                        )
                    card += "</div>"
                if snippet_html:
                    card += f'<div class="rec-excerpt">{snippet_html}</div>'
                card += "</div>"

                st.markdown(card, unsafe_allow_html=True)

    filter_review_ids = {
        int(r["review_id"]) for r in recs if r.get("review_id") is not None
    }

    intersection_ids: set[int] = set()
    if free_text and max_distance is not None:
        intersection_ids = rag_allowed_ids.intersection(filter_review_ids)

    chat_top_n = 10

    # Left: full ranking list (filters / profile), visually separate panel.
    with col_left, st.container(border=True):
        st.markdown(
            '<div class="rec-pane-header rec-pane-header-filter">'
            '<div class="rec-eyebrow">Profil &amp; Filter</div>'
            '<div class="rec-pane-title">Rangliste</div>'
            '<div class="rec-pane-sub">Sortierte Empfehlungen aus deinen '
            "Communities und Filtern. Passt auch der Freitext, wirken die "
            "Karten etwas hervorgehoben.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        _render_filter_cards(
            recs,
            rag_match=intersection_ids,
        )

    # Right column: semantic hits below chat (same bordered panel).
    with results_placeholder.container():
        st.markdown(
            '<div class="rec-results-divider">'
            '<div class="rec-results-label">Semantische Treffer</div>'
            '<div class="rec-results-title">Zur aktuellen Beschreibung</div>'
            "</div>",
            unsafe_allow_html=True,
        )

        if not free_text or max_distance is None:
            st.markdown(
                '<div class="rec-callout rec-callout-info">Schreib eine kurze '
                "Beschreibung im Chat darueber - dann erscheinen hier die Alben, "
                "die inhaltlich am besten passen.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"Aktive Freitext-Variante: **{rag_strategy}**")
            if intersection_ids:
                st.markdown(
                    '<div class="rec-pane-sub" style="margin:0 0 0.75rem 0;">'
                    "Schnittmenge mit deiner linken Rangliste - sortiert nach "
                    "nahe am Freitext.</div>",
                    unsafe_allow_html=True,
                )
                intersection_recs_all = [
                    r for r in recs if int(r["review_id"]) in intersection_ids
                ]
                intersection_recs_sorted = sorted(
                    intersection_recs_all,
                    key=lambda r: float(
                        rag_hits_by_id.get(int(r["review_id"]), {}).get("distance")
                        or 999.0,
                    ),
                )[:chat_top_n]
                rag_match_set = {int(r["review_id"]) for r in intersection_recs_sorted}
                _render_filter_cards(
                    intersection_recs_sorted,
                    rag_match=rag_match_set,
                )
            else:
                st.markdown(
                    '<div class="rec-callout rec-callout-warn">Keine Ueberschneidung '
                    "mit der linken Rangliste bei aktuellem Distanz-Limit. "
                    "Darunter: die besten rein semantischen Treffer (ggf. ausserhalb "
                    "deiner Filter).</div>",
                    unsafe_allow_html=True,
                )

                rag_allowed_hits = [
                    h for rid, h in rag_hits_by_id.items() if rid in rag_allowed_ids
                ]
                top_hits = sorted(
                    rag_allowed_hits,
                    key=lambda h: float(h.get("distance") or 999.0),
                )[:chat_top_n]

                if not top_hits:
                    st.markdown(
                        '<div class="rec-callout">Kein Treffer innerhalb der '
                        "gewaehlten Maximal-Distanz. Regler lockern oder Text "
                        "anpassen.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    # RAG-only hits: Score & Genre-Abdeckung wie bei normalen Karten.
                    genre_labels = load_genre_labels_res_10()
                    communities = load_communities_res_10()
                    comm_by_id: dict[str, dict[str, Any]] = {
                        str(c.get("id")): c for c in communities if c.get("id")
                    }
                    affinities = _load_affinities()
                    affinities_by_review_id: dict[int, dict[str, Any]] = {
                        obj["review_id"]: obj
                        for obj in affinities
                        if isinstance(obj.get("review_id"), int)
                    }
                    reviews_rag, _ = _load_reviews_and_metadata()
                    review_index_rag = {int(r.id): r for r in reviews_rag}
                    rag_memberships = load_community_memberships()

                    fs_rag = st.session_state.get("filter_settings") or {}
                    crossover_w_rag = float(
                        fs_rag.get(
                            "community_spectrum_crossover",
                            RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
                        )
                    )
                    ra = fs_rag.get("overall_weight_alpha")
                    rb = fs_rag.get("overall_weight_beta")
                    rc = fs_rag.get("overall_weight_gamma")
                    if ra is not None and rb is not None and rc is not None:
                        rag_alpha, rag_beta, rag_gamma = normalize_overall_weights(
                            float(ra),
                            float(rb),
                            float(rc),
                        )
                    else:
                        rag_alpha, rag_beta, rag_gamma = (
                            get_recommendation_overall_weights()
                        )

                    def _score_for_review_id(
                        rid: int,
                    ) -> tuple[float, float, float, list[dict[str, Any]], int]:
                        """S_a, breadth_raw, purity_raw, top tags, k_hits (aff.>0)."""
                        obj = affinities_by_review_id.get(rid)
                        if not obj:
                            return 0.0, 0.0, 0.0, [], 0
                        comms_any = obj.get("communities", {})
                        if not isinstance(comms_any, dict):
                            return 0.0, 0.0, 0.0, [], 0
                        entries_any = comms_any.get("res_10")
                        if not isinstance(entries_any, list):
                            return 0.0, 0.0, 0.0, [], 0

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
                            w = float(weights_raw.get(cid, 1.0))
                            contrib = w * val
                            s += contrib
                            if val > 0:
                                k_hits += 1
                                max_wv = max(max_wv, contrib)

                        rev = review_index_rag.get(rid)
                        if rev is not None:
                            rm = reference_community_position_masses(
                                rev,
                                rag_memberships,
                                res_key="res_10",
                                w_min=REFERENCE_POSITION_W_MIN,
                            )
                            breadth_raw = breadth_raw_from_selected_community_masses(
                                rm,
                                selected_comms,
                                weights_raw,
                            )
                        else:
                            breadth_raw = 0.0
                        purity_raw = purity_max_weighted_share(max_wv, s)

                        sorted_entries = sorted(
                            [
                                e
                                for e in entries_any
                                if isinstance(e, dict)
                                and isinstance(e.get("score"), (int, float))
                            ],
                            key=lambda e: float(e.get("score", 0.0)),
                            reverse=True,
                        )
                        top_entries = sorted_entries[:3]

                        top_comms: list[dict[str, Any]] = []
                        for e in top_entries:
                            cid = str(e.get("id"))
                            aff = float(e.get("score", 0.0))
                            label = genre_labels.get(cid)
                            c_obj = comm_by_id.get(cid)
                            if not label and isinstance(c_obj, dict):
                                centroid = c_obj.get("centroid")
                                if centroid:
                                    label = str(centroid)
                            if not label:
                                label = f"Community {cid}"
                            top_comms.append(
                                {"id": cid, "label": label, "affinity": aff},
                            )

                        return s, breadth_raw, purity_raw, top_comms, k_hits

                    pseudo_recs: list[dict[str, Any]] = []
                    rag_match_set: set[int] = set()
                    for h in top_hits:
                        rid_val = h.get("review_id")
                        if not isinstance(rid_val, int):
                            continue
                        rid = rid_val
                        score_val, br_raw, pur_raw, top_comms, kh = (
                            _score_for_review_id(rid)
                        )
                        r_raw = h.get("rating")
                        if r_raw is None:
                            rating_v = None
                        elif isinstance(r_raw, (int, float)):
                            rating_v = float(r_raw)
                        else:
                            try:
                                rating_v = float(r_raw)
                            except (TypeError, ValueError):
                                rating_v = None
                        eff_r = effective_plattentests_rating(
                            rating_v,
                            default_when_missing=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
                        )
                        pseudo_recs.append(
                            {
                                "review_id": rid,
                                "artist": h.get("artist") or "",
                                "album": h.get("album") or "",
                                "url": h.get("url") or "",
                                "rating": rating_v,
                                "rating_effective": eff_r,
                                "year": h.get("release_year"),
                                "release_date": h.get("release_date"),
                                "labels": h.get("labels") or "",
                                "score": score_val,
                                "purity_raw": pur_raw,
                                "breadth_raw": br_raw,
                                "k_hits": kh,
                                "hits_pct": 100.0 * br_raw,
                                "top_communities": top_comms,
                                "text": h.get("chunk_text") or h.get("text") or "",
                            }
                        )
                        rag_match_set.add(rid)

                    pr_pur = [float(p["purity_raw"]) for p in pseudo_recs]
                    pr_br = [float(p["breadth_raw"]) for p in pseudo_recs]
                    pr_pur_n, pr_br_n, pr_spec_n = community_spectrum_norm_batch(
                        pr_pur,
                        pr_br,
                        crossover_weight=crossover_w_rag,
                    )
                    for p, pn, bn, sn in zip(
                        pseudo_recs,
                        pr_pur_n,
                        pr_br_n,
                        pr_spec_n,
                        strict=True,
                    ):
                        rn = rating_to_unit_interval(
                            p["rating"],
                            default_on_10_scale=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
                        )
                        p["purity_norm"] = pn
                        p["breadth_norm"] = bn
                        p["community_spectrum_norm"] = sn
                        sn_eff, sn_gate = gated_community_spectrum(
                            float(sn),
                            float(p["score"]),
                        )
                        p["spectrum_matching_gate"] = sn_gate
                        p["community_spectrum_effective"] = sn_eff
                        p["rating_norm"] = rn
                        p["overall_score"] = overall_score(
                            float(p["score"]),
                            rn,
                            sn_eff,
                            alpha=rag_alpha,
                            beta=rag_beta,
                            gamma=rag_gamma,
                        )

                    _render_filter_cards(
                        pseudo_recs,
                        rag_match=rag_match_set,
                    )

    st.markdown("---")
    col_back, col_start = st.columns([1, 1])
    with col_back:
        if st.button("Filter anpassen", key=KEY_FILTER_ADJUST_BUTTON):
            st.switch_page("pages/5_Filter_Flow.py")
    with col_start:
        if st.button("Start new workflow", key=KEY_START_WORKFLOW_BUTTON):
            saved_slug = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.clear()
            if saved_slug is not None:
                st.session_state[ACTIVE_PROFILE_SESSION_KEY] = saved_slug
            st.switch_page("streamlit_app.py")


if __name__ == "__main__":
    main()
