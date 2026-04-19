"""Neueste Rezensionen aus dem lokalen Corpus mit Community-/Genre-Tags."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st
from pages.neueste_reviews_pool import (
    RECENT_DEFAULT,
    RES_KEY,
    ensure_neueste_session_defaults,
    fetch_newest_reviews_pool,
)
from pages.page_helpers import (
    community_display_label,
    format_record_labels_for_card,
    get_selected_communities,
    inject_recommendation_flow_shell_css,
    load_communities_res_10,
    load_genre_labels_res_10,
    recommendation_card_community_tags_html,
    recommendation_card_meta_parts,
    release_year_for_card_meta,
    render_toolbar,
)

from music_review.config import (
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    resolve_data_path,
)
from music_review.dashboard.neueste_batch_score_chart import (
    build_newest_batch_score_figure,
    newest_batch_score_chart_config,
    newest_batch_score_scale_explanation,
)
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects

_NEWEST_EXTRA_CSS = """
        span.rec-title {
            font-size: 1.08rem;
            font-weight: 600;
            color: #1f2937;
            letter-spacing: -0.01em;
        }
        .rec-newest-cards-spacer {
            height: 1.35rem;
            min-height: 1.35rem;
            margin: 0;
            padding: 0;
            line-height: 0;
            font-size: 0;
        }
        [data-testid="element-container"]:has([data-testid="stPlotlyChart"]) {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stPlotlyChart"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stMarkdownContainer"] p.rec-newest-score-explain {
            color: rgba(49, 51, 63, 0.66);
            font-size: 0.875rem;
            line-height: 1.45;
            margin: -2rem 0 0.65rem 0 !important;
            padding: 0 !important;
        }
"""


def _newest_css() -> None:
    inject_recommendation_flow_shell_css(extra_rules=_NEWEST_EXTRA_CSS)


@st.cache_data(ttl=3600)
def _load_affinity_top_map(*, top_k: int = 5) -> dict[int, list[tuple[str, float]]]:
    path = resolve_data_path("data/album_community_affinities.jsonl")
    if not path.is_file():
        return {}
    result: dict[int, list[tuple[str, float]]] = {}
    for obj in iter_jsonl_objects(path, log_errors=False):
        review_id = obj.get("review_id")
        comms = (obj.get("communities") or {}).get(RES_KEY)
        if not isinstance(review_id, int) or not isinstance(comms, list):
            continue
        items: list[tuple[str, float]] = []
        for entry in comms:
            if not isinstance(entry, dict):
                continue
            cid = entry.get("id")
            score = entry.get("score")
            if isinstance(cid, str) and isinstance(score, (int, float)):
                items.append((cid, float(score)))
        if not items:
            continue
        items.sort(key=lambda t: t[1], reverse=True)
        result[review_id] = items[:top_k]
    return result


def _top_communities_display(
    review_id: int,
    aff_map: dict[int, list[tuple[str, float]]],
    genre_labels: dict[str, str],
    comm_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid, aff in aff_map.get(review_id, []):
        c_obj = comm_by_id.get(cid)
        label = community_display_label(
            cid,
            genre_labels,
            c_obj if isinstance(c_obj, dict) else None,
        )
        out.append({"id": cid, "label": label, "affinity": aff})
    return out


def _render_newest_card(
    review: Review,
    rank: int,
    top_comms: list[dict[str, Any]],
    *,
    overall_score: float | None = None,
    filter_selected_community_ids: set[str] | frozenset[str] | None = None,
) -> None:
    """Same card markup as ``6_Recommendations_Flow._render_filter_cards``."""
    artist = review.artist or ""
    album = review.album or ""
    url = review.url or ""
    title = f"{html.escape(str(artist))} — {html.escape(str(album))}"
    if url:
        la = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
        title_html = f'<a {la} class="rec-title">{title}</a>'
    else:
        title_html = f'<span class="rec-title">{title}</span>'
    rank_html = f'<span class="rec-rank" aria-label="Platz {rank}">{rank}</span>'

    year_val = release_year_for_card_meta(review)
    labels_str = format_record_labels_for_card(None, review.labels)
    use_score = overall_score is not None
    overall_val = float(overall_score) if use_score else 0.0
    rating_v = float(review.rating) if review.rating is not None else None
    meta_parts = recommendation_card_meta_parts(
        review.release_date,
        year_val,
        rating_v,
        overall_val,
        labels_str,
        default_rating=RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
        include_overall_score=use_score,
    )
    meta_html = html.escape(" · ".join(meta_parts))

    snippet_source = review.text or ""
    snippet = snippet_source[:260] + ("..." if len(snippet_source) > 260 else "")

    card = '<div class="rec-card">'
    card += f'<div class="rec-header">{rank_html}{title_html}</div>'
    if meta_html:
        card += f'<div class="rec-meta">{meta_html}</div>'
    if top_comms:
        card += recommendation_card_community_tags_html(
            top_comms,
            filter_selected_community_ids=filter_selected_community_ids,
        )
    if snippet:
        card += (
            '<div class="rec-excerpt">'
            f"{html.escape(snippet).replace(chr(10), '<br>')}"
            "</div>"
        )
    card += "</div>"
    st.markdown(card, unsafe_allow_html=True)


def main() -> None:
    ensure_neueste_session_defaults()
    # Styles vor dem oberen Trennstrich (Profil in der Seitenleiste; gleiches Muster
    # wie pages/5_Filter_Flow.py).
    _newest_css()
    render_toolbar("neueste")

    selected_comms = get_selected_communities()

    st.markdown(
        '<div class="rec-hero"><p class="rec-page-title">Neueste Rezensionen</p></div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown(
            '<p class="rec-sort-section-label">'
            "Angezeigte Anzahl der zuletzt rezensierten Alben</p>",
            unsafe_allow_html=True,
        )
        n_show = st.slider(
            "Wie viele der neuesten Alben anzeigen",
            min_value=5,
            max_value=50,
            value=RECENT_DEFAULT,
            label_visibility="collapsed",
        )

    reviews, ranked_rows = fetch_newest_reviews_pool(n_show)

    if not reviews:
        st.markdown(
            '<div class="rec-callout rec-callout-warn">'
            "Keine Reviews gefunden. Pfad prüfen: <code>data/reviews.jsonl</code> "
            "(ggf. Scraping ausführen)."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    if ranked_rows is not None:
        with st.container(border=True):
            scores = [float(r["overall_score"]) for r in ranked_rows]
            st.markdown(
                '<p class="rec-sort-section-label">'
                "Wie gut passen die neuesten Alben zu deinen präferierten Musik-Stilen?"
                "</p>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                build_newest_batch_score_figure(scores),
                width="stretch",
                config=newest_batch_score_chart_config(),
            )
            _scale_txt = html.escape(newest_batch_score_scale_explanation())
            st.markdown(
                f'<p class="rec-newest-score-explain">{_scale_txt}</p>',
                unsafe_allow_html=True,
            )

    aff_map = _load_affinity_top_map(top_k=5)
    genre_labels = load_genre_labels_res_10()
    communities = load_communities_res_10()
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    missing_aff = sum(1 for r in reviews if r.id not in aff_map)
    if missing_aff:
        st.markdown(
            '<div class="rec-callout rec-callout-info">Hinweis: Zu einigen der '
            "angezeigten Alben fehlen Zuordnungsdaten für die Stil-Tags "
            "(Datenstand ggf. veraltet).</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="rec-newest-cards-spacer" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    if ranked_rows is not None:
        for i, row in enumerate(ranked_rows):
            rank = i + 1
            rev = row["review"]
            top = _top_communities_display(
                int(rev.id),
                aff_map,
                genre_labels,
                comm_by_id,
            )
            _render_newest_card(
                rev,
                rank,
                top,
                overall_score=float(row["overall_score"]),
                filter_selected_community_ids=selected_comms,
            )
    else:
        for i, review in enumerate(reviews):
            rank = i + 1
            top = _top_communities_display(
                int(review.id),
                aff_map,
                genre_labels,
                comm_by_id,
            )
            _render_newest_card(
                review,
                rank,
                top,
                filter_selected_community_ids=selected_comms,
            )


main()
