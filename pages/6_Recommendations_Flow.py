from __future__ import annotations

import html
import random
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
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
from music_review.dashboard.recommendations_flow_pagination import (
    DEFAULT_RECOMMENDATIONS_PAGE_SIZE,
    RECOMMENDATIONS_PAGE_SIZE_CHOICES,
    clamp_recommendation_page,
    count_albums_on_next_page,
    parse_page_size_choice,
    recommendation_page_slice_bounds,
    recommendation_total_pages,
    streamlit_parent_scroll_to_anchor_html,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    apply_profile_to_session,
    default_profiles_dir,
    load_profile,
)
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.pipeline.retrieval.reference_graph import (
    reference_community_position_masses,
)

REC_PAGE_SIZE_SELECT_OPTIONS: tuple[str, ...] = (
    *(str(n) for n in RECOMMENDATIONS_PAGE_SIZE_CHOICES),
    "Alle",
)
REC_PAGE_SIZE_DEFAULT_INDEX = RECOMMENDATIONS_PAGE_SIZE_CHOICES.index(
    DEFAULT_RECOMMENDATIONS_PAGE_SIZE
)

# Streamlit widget keys: keep centralized to avoid accidental duplicates.
KEY_START_WORKFLOW_BUTTON = "rec_start_workflow_button"
KEY_PAGE_SIZE_PREV = "rec_page_size_prev"
KEY_REC_PAGE = "rec_results_page_1based"
KEY_SCROLL_REC_LIST = "rec_scroll_to_list_after_page_change"
LEGACY_KEY_VISIBLE_COUNT = "rec_visible_count"

_REC_LIST_SCROLL_ANCHOR_ID = "music-review-rec-list-top"


_REC_PAGE_SIZE_HEADING_CSS = """
        .rec-sort-section-label.rec-page-size-heading {
            margin-top: 1.35rem;
        }
        .rec-list-scroll-anchor {
            scroll-margin-top: 1rem;
        }
"""


def _recommendations_css() -> None:
    inject_recommendation_flow_shell_css(
        include_chat_avatar_style=False,
        extra_rules=_REC_PAGE_SIZE_HEADING_CSS,
    )


def _inject_scroll_to_recommendation_list() -> None:
    """Nach Seitenwechsel zum Anfang der Ergebnisliste scrollen."""
    components.html(
        streamlit_parent_scroll_to_anchor_html(
            anchor_element_id=_REC_LIST_SCROLL_ANCHOR_ID,
        ),
        height=0,
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


def _render_sort_settings_widgets_and_persist() -> None:
    """Ranglisten-Modus und Zufallsanteil; schreibt in ``filter_settings``.

    Erwartet einen umgebenden Container (z. B. ``st.container(border=True)``).
    """
    fs: dict[str, Any] = dict(st.session_state.get("filter_settings") or {})
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
    fs["rag_query_strategy"] = "B"
    st.session_state["filter_settings"] = fs


def main() -> None:
    render_toolbar("recommendations")
    _recommendations_css()

    st.markdown(
        '<div class="rec-hero">'
        '<p class="rec-page-title">Deine Empfehlungen</p>'
        '<div id="rec-page-desc-wrap">'
        '<p class="rec-page-desc">Basierend auf deinen gewählten Stil-Schwerpunkten '
        "und Filtereinstellungen.</p>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        _render_sort_settings_widgets_and_persist()
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
            st.page_link(
                "pages/5_Filter_Flow.py",
                label="Zurück zu den Filtern",
                use_container_width=True,
            )
            return

        st.markdown(
            '<p class="rec-sort-section-label rec-page-size-heading">'
            "Anzahl der gleichzeitig angezeigten Alben</p>",
            unsafe_allow_html=True,
        )
        size_label = st.selectbox(
            "Alben pro Ladung",
            options=REC_PAGE_SIZE_SELECT_OPTIONS,
            index=REC_PAGE_SIZE_DEFAULT_INDEX,
            key="rec_page_size_select",
            label_visibility="collapsed",
        )
        st.markdown(f"{len(recs)} Alben entsprechen aktuell deinen Kriterien.")
    page_size = parse_page_size_choice(size_label)
    prev_ps: int | None = st.session_state.get(KEY_PAGE_SIZE_PREV)
    if prev_ps != page_size:
        st.session_state.pop(KEY_REC_PAGE, None)
        st.session_state.pop(LEGACY_KEY_VISIBLE_COUNT, None)
    st.session_state[KEY_PAGE_SIZE_PREV] = page_size

    if (
        KEY_REC_PAGE not in st.session_state
        and LEGACY_KEY_VISIBLE_COUNT in st.session_state
        and page_size is not None
        and page_size > 0
    ):
        legacy_raw = st.session_state.get(LEGACY_KEY_VISIBLE_COUNT)
        if isinstance(legacy_raw, (int, float)):
            legacy_vis = int(legacy_raw)
            migrated = max(1, (legacy_vis + page_size - 1) // page_size)
            st.session_state[KEY_REC_PAGE] = migrated
        st.session_state.pop(LEGACY_KEY_VISIBLE_COUNT, None)

    selected_comms = get_selected_communities()

    def _render_filter_cards(
        rec_list: list[dict[str, Any]],
        *,
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

            snippet_source = rec.get("text") or ""
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

            card = '<div class="rec-card">'
            card += f'<div class="rec-header">{rank_html}{title_html}</div>'
            if meta_html:
                card += f'<div class="rec-meta">{meta_html}</div>'
            if top_comms:
                card += recommendation_card_community_tags_html(
                    top_comms,
                    filter_selected_community_ids=selected_comms,
                )
            if snippet:
                card += (
                    '<div class="rec-excerpt">'
                    f"{html.escape(snippet).replace(chr(10), '<br>')}"
                    "</div>"
                )
            card += "</div>"
            st.markdown(card, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Rangliste (filter-based ranking), seitenweise
    # ------------------------------------------------------------------
    if page_size is None:
        _render_filter_cards(recs)
    else:
        total_pages = recommendation_total_pages(total=len(recs), page_size=page_size)
        raw_page = st.session_state.get(KEY_REC_PAGE)
        page_one = int(raw_page) if raw_page is not None else 1
        page_one = clamp_recommendation_page(page_one, total_pages)
        st.session_state[KEY_REC_PAGE] = page_one
        start_idx, end_idx = recommendation_page_slice_bounds(
            page_one_based=page_one,
            page_size=page_size,
            total=len(recs),
        )
        st.markdown(
            f'<div id="{html.escape(_REC_LIST_SCROLL_ANCHOR_ID)}" '
            'class="rec-list-scroll-anchor"></div>',
            unsafe_allow_html=True,
        )
        _render_filter_cards(
            recs[start_idx:end_idx],
            rank_start=start_idx + 1,
        )
        if st.session_state.pop(KEY_SCROLL_REC_LIST, False):
            _inject_scroll_to_recommendation_list()
        st.caption(f"Seite {page_one} von {total_pages}")
        prev_col, next_col = st.columns(2)
        with prev_col:
            if page_one > 1 and st.button(
                "Vorherige Seite",
                key="rec_page_prev",
            ):
                st.session_state[KEY_REC_PAGE] = page_one - 1
                st.session_state[KEY_SCROLL_REC_LIST] = True
                st.rerun()
        with next_col:
            if page_one < total_pages:
                n_next = count_albums_on_next_page(
                    current_page_one_based=page_one,
                    page_size=page_size,
                    total=len(recs),
                )
                next_page_num = page_one + 1
                if st.button(
                    "Zeige nächste "
                    f"{n_next} Alben (Seite {next_page_num} von {total_pages})",
                    key="rec_page_next",
                ):
                    st.session_state[KEY_REC_PAGE] = next_page_num
                    st.session_state[KEY_SCROLL_REC_LIST] = True
                    st.rerun()

    st.markdown("---")
    col_back, col_start = st.columns([1, 1])
    with col_back:
        st.page_link(
            "pages/5_Filter_Flow.py",
            label="Filter anpassen",
            use_container_width=True,
        )
    with col_start:
        if st.button("Von vorn beginnen", key=KEY_START_WORKFLOW_BUTTON):
            saved_slug = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.clear()
            if saved_slug is not None:
                st.session_state[ACTIVE_PROFILE_SESSION_KEY] = saved_slug
                loaded = load_profile(default_profiles_dir(), str(saved_slug))
                if loaded is not None:
                    apply_profile_to_session(st.session_state, loaded)
            st.switch_page("pages/0b_Einstieg.py")


if __name__ == "__main__":
    main()
