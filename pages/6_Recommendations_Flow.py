from __future__ import annotations

import html
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
    inject_recommendation_flow_shell_css,
    load_communities_res_10,
    load_community_memberships,
    load_genre_labels_res_10,
    load_sorted_unique_plattenlabels_from_reviews,
    max_release_year_from_corpus,
    min_release_year_from_corpus,
    plattenlabel_filter_passes,
    recommendation_card_community_tags_html,
    recommendation_card_meta_parts,
    render_toolbar,
)

from music_review.config import (
    RECOMMENDATION_DEFAULT_COMMUNITY_CROSSOVER,
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
KEY_VISIBLE_COUNT = "rec_visible_count"

CARDS_PER_PAGE = 25

# Freitext-RAG: max. reviews after fusion (N). Top-k per variant must be large
# enough that fusion can reach N (chunk overlap + strategy A = single variant).
RAG_FUSION_N_RESULTS = 2500
RAG_TOP_K_PER_VARIANT = 2500
# Freitext-RAG: feste Query-Varianten-Strategie (kein UI; nur Backend).
RAG_FREETEXT_QUERY_STRATEGY = "B"


def _recommendations_css() -> None:
    inject_recommendation_flow_shell_css(include_chat_avatar_style=True)


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
    strategy: str = RAG_FREETEXT_QUERY_STRATEGY,
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
    sm_raw = str(filter_settings.get("sort_mode", _SORT_MODE_FIXED))
    sort_mode = _SORT_MODE_MIGRATION.get(sm_raw, sm_raw)
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

    platten_all = load_sorted_unique_plattenlabels_from_reviews()
    plat_sel = filter_settings.get("plattenlabel_selection")

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

        # Aufbereitete Top-Community-Infos für die Darstellung
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

    # Immer zuerst nach echtem Gesamtscore; Serendipity mischt die Reihenfolge
    # (Spearman-Rangkorrelation vor/nachher grob ~ 1 - s).
    candidates.sort(key=lambda x: float(x["overall_score"]), reverse=True)
    if sort_mode == _SORT_MODE_RANDOM and serendipity > 0.0:
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


_SORT_MODE_FIXED = "Feste Reihenfolge"
_SORT_MODE_RANDOM = "Mit Zufall"

_SORT_MODE_MIGRATION: dict[str, str] = {
    "Deterministisch": _SORT_MODE_FIXED,
    "Serendipity": _SORT_MODE_RANDOM,
}


def _render_sort_settings_and_persist() -> None:
    """Ranglisten-Modus und Zufallsanteil; merged in ``filter_settings``."""
    fs: dict[str, Any] = dict(st.session_state.get("filter_settings") or {})
    with st.container(border=True):
        st.markdown(
            '<p class="rec-sort-section-label">Sortierung und Zufall</p>',
            unsafe_allow_html=True,
        )
        col_sort, col_ser = st.columns(2)
        with col_sort:
            sm_raw = str(fs.get("sort_mode", _SORT_MODE_FIXED))
            sm_def = _SORT_MODE_MIGRATION.get(sm_raw, sm_raw)
            sort_mode = st.selectbox(
                "Reihenfolge",
                options=[_SORT_MODE_FIXED, _SORT_MODE_RANDOM],
                index=0 if sm_def == _SORT_MODE_FIXED else 1,
                help=(
                    "Feste Reihenfolge: Alben werden strikt nach "
                    "Score sortiert. Mit Zufall: Die Liste wird etwas "
                    "durchgemischt, damit du auch Alben entdeckst, "
                    "die sonst weiter unten stehen."
                ),
            )
        with col_ser:
            ser_def = float(fs.get("serendipity", 0.0))
            serendipity = st.slider(
                "Zufallsanteil (0 = stabil, 1 = stark gemischt)",
                min_value=0.0,
                max_value=1.0,
                value=ser_def,
                step=0.1,
                disabled=(sort_mode != _SORT_MODE_RANDOM),
                help=(
                    "Bestimmt, wie stark die Liste durchgemischt wird. "
                    "0 bedeutet kaum Veränderung, 1 mischt die "
                    "Reihenfolge fast komplett zufällig durch."
                ),
            )
        fs["sort_mode"] = sort_mode
        fs["serendipity"] = serendipity
        fs["rag_query_strategy"] = RAG_FREETEXT_QUERY_STRATEGY
        st.session_state["filter_settings"] = fs


def _render_semantic_only_cards(
    top_hits: list[dict[str, Any]],
    *,
    selected_comms: dict[str, float],
    weights_raw: dict[str, float],
    render_fn: Any,
) -> None:
    """Score RAG-only hits and render them as recommendation cards."""
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

    fs_rag: dict[str, Any] = st.session_state.get("filter_settings") or {}
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
        rag_alpha, rag_beta, rag_gamma = get_recommendation_overall_weights()

    def _score_for_review_id(
        rid: int,
    ) -> tuple[float, float, float, list[dict[str, Any]], int]:
        """Return S_a, breadth_raw, purity_raw, top tags, k_hits."""
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
                if isinstance(e, dict) and isinstance(e.get("score"), (int, float))
            ],
            key=lambda e: float(e.get("score", 0.0)),
            reverse=True,
        )
        top_entries = sorted_entries[:3]

        top_comms: list[dict[str, Any]] = []
        for e in top_entries:
            cid = str(e.get("id"))
            aff = float(e.get("score", 0.0))
            c_obj = comm_by_id.get(cid)
            label = community_display_label(
                cid,
                genre_labels,
                c_obj if isinstance(c_obj, dict) else None,
            )
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
        score_val, br_raw, pur_raw, top_comms, kh = _score_for_review_id(rid)
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
        rev_for_card = review_index_rag.get(rid)
        pseudo_label_str = format_record_labels_for_card(
            h.get("labels"),
            rev_for_card.labels if rev_for_card is not None else None,
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
                "labels": pseudo_label_str,
                "score": score_val,
                "purity_raw": pur_raw,
                "breadth_raw": br_raw,
                "k_hits": kh,
                "hits_pct": 100.0 * br_raw,
                "top_communities": top_comms,
                "text": h.get("chunk_text") or h.get("text") or "",
            },
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

    render_fn(pseudo_recs, rag_match=rag_match_set)


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Empfehlungen",
        page_icon=None,
        layout="centered",
    )

    render_toolbar("recommendations")
    _recommendations_css()

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Deine Empfehlungen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Basierend auf deinen gewählten Stil-Schwerpunkten, '
        "Filtereinstellungen und (optional) deiner Stimmungsbeschreibung.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    _render_sort_settings_and_persist()
    recs = _compute_recommendations()

    if not recs:
        st.markdown(
            '<div class="rec-callout rec-callout-warn">'
            "Es konnten keine passenden Alben auf Basis der aktuellen Auswahl "
            "und Filter gefunden werden. Du kannst die Filter zurücknehmen oder "
            "andere Stil-Schwerpunkte wählen."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Zurück zu den Filtern"):
            st.switch_page("pages/5_Filter_Flow.py")
        return

    st.markdown(f"**{len(recs)} Alben entsprechen aktuell deinen Kriterien.**")

    selected_comms = get_selected_communities()
    weights_raw: dict[str, float] = st.session_state.get("community_weights_raw") or {}

    rag_hits_by_id: dict[int, dict[str, Any]] = {}

    def _render_filter_cards(
        rec_list: list[dict[str, Any]],
        *,
        rag_match: set[int],
        rank_start: int = 1,
    ) -> None:
        for idx, rec in enumerate(rec_list):
            rank = rank_start + idx
            artist = rec.get("artist") or ""
            album = rec.get("album") or ""
            url = rec.get("url") or ""
            rating = rec.get("rating")
            year = rec.get("year")
            labels = rec.get("labels") or ""
            overall = float(rec.get("overall_score") or 0.0)
            top_comms = rec.get("top_communities") or []

            is_rag = False
            hit: dict[str, Any] | None = None
            if rec.get("review_id") in rag_match:
                hit = rag_hits_by_id.get(int(rec["review_id"]))
                if hit and isinstance(hit.get("distance"), (int, float)):
                    is_rag = True

            snippet_source = rec.get("text") or ""
            if is_rag and hit:
                snippet_source = (
                    hit.get("chunk_text") or hit.get("text") or snippet_source
                )
            snippet = snippet_source[:260] + (
                "..." if len(snippet_source) > 260 else ""
            )

            title = f"{html.escape(str(artist))} — {html.escape(str(album))}"
            if url:
                la = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
                title_html = f'<a {la} class="rec-title">{title}</a>'
            else:
                title_html = f'<span class="rec-title">{title}</span>'
            rank_html = (
                f'<span class="rec-rank" aria-label="Platz {rank}">{rank}</span>'
            )

            meta_parts = recommendation_card_meta_parts(
                rec.get("release_date"),
                year,
                rating,
                overall,
                labels,
                default_rating=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
            )
            meta_html = html.escape(" · ".join(meta_parts))

            card_cls = "rec-card rec-card-rag" if is_rag else "rec-card"
            card = f'<div class="{card_cls}">'
            card += f'<div class="rec-header">{rank_html}{title_html}</div>'
            if meta_html:
                card += f'<div class="rec-meta">{meta_html}</div>'
            if top_comms:
                card += recommendation_card_community_tags_html(top_comms)
            if snippet:
                card += (
                    '<div class="rec-excerpt">'
                    f"{html.escape(snippet).replace(chr(10), '<br>')}"
                    "</div>"
                )
            card += "</div>"
            st.markdown(card, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Rangliste (filter-based ranking)
    # ------------------------------------------------------------------
    visible = int(
        st.session_state.get(KEY_VISIBLE_COUNT) or CARDS_PER_PAGE,
    )
    visible = max(CARDS_PER_PAGE, min(visible, len(recs)))
    _render_filter_cards(
        recs[:visible],
        rag_match=set(),
    )
    if visible < len(recs):
        remaining = len(recs) - visible
        batch = min(CARDS_PER_PAGE, remaining)
        if st.button(
            f"Mehr anzeigen ({batch} weitere von {remaining})",
            key="rec_show_more",
        ):
            st.session_state[KEY_VISIBLE_COUNT] = visible + batch
            st.rerun()

    # ------------------------------------------------------------------
    # Semantische Suche
    # ------------------------------------------------------------------
    with st.container(border=True):
        st.markdown(
            '<div class="rec-pane-header rec-pane-header-semantic">'
            '<div class="rec-eyebrow">Semantische Suche</div>'
            '<div class="rec-pane-title">Finetuning im Dialog</div>'
            '<div class="rec-pane-sub">Beschreibe Stimmung, Klang oder '
            "Inhalte. Darunter erscheinen die Alben, die semantisch "
            "am besten passen.</div>"
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

        chat_input = st.chat_input(
            "Stimmung oder Inhalte beschreiben …",
            key=KEY_CHAT_INPUT,
        )
        if chat_input is not None:
            chat_input_clean = chat_input.strip()
            st.session_state["free_text_query"] = chat_input_clean
            if chat_input_clean:
                chat_messages.append({"role": "user", "content": chat_input_clean})
                chat_messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Alles klar - ich passe die Trefferliste "
                            "an deine Beschreibung an."
                        ),
                    },
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
            "Ähnlichkeit (niedriger = passender)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.05,
            disabled=not bool(free_text),
            key=KEY_RAG_MAX_DISTANCE,
        )

    # ------------------------------------------------------------------
    # RAG-Abgleich (Freitext)
    # ------------------------------------------------------------------
    free_text = (st.session_state.get("free_text_query") or "").strip()
    max_distance = float(rag_max_distance_ui) if free_text else None
    rag_allowed_ids: set[int] = set()

    if free_text:
        try:
            rag_hits = _search_rag_hits(free_text)
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

    filter_review_ids = {
        int(r["review_id"]) for r in recs if r.get("review_id") is not None
    }

    intersection_ids: set[int] = set()
    if free_text and max_distance is not None:
        intersection_ids = rag_allowed_ids.intersection(filter_review_ids)

    chat_top_n = 10

    # ------------------------------------------------------------------
    # Semantische Treffer
    # ------------------------------------------------------------------
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
            "Beschreibung im Chat - dann erscheinen hier die Alben, "
            "die inhaltlich am besten passen.</div>",
            unsafe_allow_html=True,
        )
    else:
        if intersection_ids:
            st.markdown(
                '<div class="rec-pane-sub" style="margin:0 0 0.75rem 0;">'
                "Schnittmenge mit deiner Rangliste - sortiert nach "
                "Nähe zum Freitext.</div>",
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
                '<div class="rec-callout rec-callout-warn">Keine Überschneidung '
                "mit der Rangliste bei aktuellem Distanz-Limit. "
                "Darunter: die besten rein semantischen Treffer (ggf. "
                "außerhalb deiner Filter).</div>",
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
                    "gewählten Maximal-Distanz. Regler lockern oder Text "
                    "anpassen.</div>",
                    unsafe_allow_html=True,
                )
            else:
                _render_semantic_only_cards(
                    top_hits,
                    selected_comms=selected_comms,
                    weights_raw=weights_raw,
                    render_fn=_render_filter_cards,
                )

    st.markdown("---")
    col_back, col_start = st.columns([1, 1])
    with col_back:
        if st.button("Filter anpassen", key=KEY_FILTER_ADJUST_BUTTON):
            st.switch_page("pages/5_Filter_Flow.py")
    with col_start:
        if st.button("Von vorn beginnen", key=KEY_START_WORKFLOW_BUTTON):
            saved_slug = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.clear()
            if saved_slug is not None:
                st.session_state[ACTIVE_PROFILE_SESSION_KEY] = saved_slug
            st.switch_page("pages/0b_Einstieg.py")


if __name__ == "__main__":
    main()
