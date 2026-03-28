"""Neueste Rezensionen aus dem lokalen Corpus mit Community-/Genre-Tags."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import streamlit as st
from pages.page_helpers import (
    community_display_label,
    format_release_date,
    get_selected_communities,
    load_communities_res_10,
    load_community_memberships,
    load_genre_labels_res_10,
    render_toolbar,
)

from music_review.config import (
    RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING,
    resolve_data_path,
)
from music_review.dashboard.preference_ranking import (
    global_breadth_norm_by_review_id,
    preference_ranked_rows,
)
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

RECENT_DEFAULT = 20
RES_KEY = "res_10"


def _newest_css() -> None:
    st.markdown(
        """
        <style>
        .nw-page-title {
            font-size: 1.6rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        .nw-page-desc { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.3rem; }
        /* Gleiche Kachel-Styles wie Empfehlungen (6_Recommendations_Flow) */
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
        </style>
        """,
        unsafe_allow_html=True,
    )


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


@st.cache_data(ttl=300)
def _load_newest_reviews(n: int) -> list[Review]:
    path = resolve_data_path("data/reviews.jsonl")
    if not path.is_file():
        return []
    reviews = load_reviews_from_jsonl(path)
    reviews.sort(key=lambda r: int(r.id), reverse=True)
    return reviews[: max(1, n)]


@st.cache_data(ttl=300)
def _load_all_reviews_for_breadth_norm() -> list[Review]:
    """Gesamtes Corpus für globales Abdeckungs-Perzentil (breadth_norm)."""
    path = resolve_data_path("data/reviews.jsonl")
    if not path.is_file():
        return []
    return load_reviews_from_jsonl(path)


@st.cache_data(ttl=300)
def _cached_global_breadth_norm_map(
    selected_key: tuple[str, ...],
    weights_key: tuple[tuple[str, float], ...],
) -> dict[int, float]:
    all_rev = _load_all_reviews_for_breadth_norm()
    if not all_rev:
        return {}
    memberships = load_community_memberships()
    weights = {k: float(v) for k, v in weights_key}
    return global_breadth_norm_by_review_id(
        all_rev,
        memberships=memberships,
        selected_comms=set(selected_key),
        weights_raw=weights,
    )


@st.cache_data(ttl=3600)
def _load_affinity_by_review_id() -> dict[int, dict[str, Any]]:
    path = Path(resolve_data_path("data/album_community_affinities.jsonl"))
    if not path.is_file():
        return {}
    out: dict[int, dict[str, Any]] = {}
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        rid = obj.get("review_id")
        if isinstance(rid, int):
            out[rid] = obj
    return out


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


def _rec_tag_colors(aff: float) -> tuple[str, str, str]:
    if aff >= 0.6:
        return "#0f766e", "#0f766e", "#ecfeff"
    if aff >= 0.3:
        return "#22c55e", "#16a34a", "#ecfdf3"
    if aff >= 0.1:
        return "#e0f2fe", "#93c5fd", "#0f172a"
    return "#f3f4f6", "#e5e7eb", "#4b5563"


def _rec_top_communities_html(top_comms: list[dict[str, Any]]) -> str:
    if not top_comms:
        return ""
    parts: list[str] = ['<div class="rec-communities">']
    for tc in top_comms:
        aff = float(tc.get("affinity") or 0.0)
        lab = str(tc.get("label") or "")
        bg, border, fg = _rec_tag_colors(aff)
        tag_text = lab
        parts.append(
            f'<span class="rec-comm-tag" '
            f'style="background-color:{bg};border-color:{border};color:{fg};">'
            f"{html.escape(tag_text)}"
            "</span>",
        )
    parts.append("</div>")
    return "".join(parts)


def _rating_line(review: Review) -> str:
    if review.rating is not None:
        return f"Rating: {float(review.rating):g}/10"
    return f"Rating: {RECOMMENDATION_RATING_DEFAULT_WHEN_MISSING:.0f}/10 (angenommen)"


def _render_newest_chronological_card(
    review: Review,
    rank: int,
    top_comms: list[dict[str, Any]],
) -> None:
    """Eine Spalte, mit Rang; ohne Präferenz-Scores (neueste ID zuerst)."""
    artist = review.artist or ""
    album = review.album or ""
    url = review.url or ""
    header = f"{html.escape(str(artist))} — {html.escape(str(album))}"
    if url:
        link = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
        header_html = f'<a {link} class="rec-title">{header}</a>'
    else:
        header_html = f'<span class="rec-title">{header}</span>'
    rank_html = f'<span class="rec-rank" aria-label="Platz {rank}">{rank}.</span>'

    label_list = review.labels or []
    label_str = ", ".join(str(x) for x in label_list) if label_list else ""
    rel = format_release_date(review.release_date, review.release_year)
    core = (
        f"{rel + ' - ' if rel else ''}"
        f"{label_str + ' - ' if label_str else ''}"
        f"{_rating_line(review)}"
        " - Sortierung: neueste zuerst"
    )
    meta_html = html.escape(core)

    snippet_source = review.text or ""
    snippet = snippet_source[:260] + ("…" if len(snippet_source) > 260 else "")
    snippet_html = html.escape(snippet).replace("\n", "<br>")

    card = '<div class="rec-card">'
    card += f'<div class="rec-header">{rank_html}{header_html}</div>'
    card += f'<div class="rec-meta">{meta_html}</div>'
    if top_comms:
        card += _rec_top_communities_html(top_comms)
    else:
        card += (
            '<div class="rec-meta">Keine Stil-Tags für dieses Album '
            "(Zuordnungsdaten fehlen).</div>"
        )
    if snippet_html:
        card += f'<div class="rec-excerpt">{snippet_html}</div>'
    card += "</div>"
    st.markdown(card, unsafe_allow_html=True)


def _render_newest_scored_card(
    row: dict[str, Any],
    rank: int,
    top_comms: list[dict[str, Any]],
) -> None:
    """Wie Filter-Kacheln in 6_Recommendations_Flow: Rang + Gesamt- und Teilscores."""
    review: Review = row["review"]
    artist = review.artist or ""
    album = review.album or ""
    url = review.url or ""
    header = f"{html.escape(str(artist))} — {html.escape(str(album))}"
    if url:
        link = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
        header_html = f'<a {link} class="rec-title">{header}</a>'
    else:
        header_html = f'<span class="rec-title">{header}</span>'
    rank_html = f'<span class="rec-rank" aria-label="Platz {rank}">{rank}.</span>'

    release_str = format_release_date(review.release_date, review.release_year)
    label_list = review.labels or []
    label_str = ", ".join(str(x) for x in label_list) if label_list else ""

    overall = float(row["overall_score"])
    score = float(row["score"])
    spec_raw = float(row["community_spectrum_norm"])
    spec_eff = float(row.get("community_spectrum_effective", spec_raw))
    spec_gate = float(row.get("spectrum_matching_gate", 1.0))
    rn = float(row["rating_norm"])
    p_n = float(row["purity_norm"])
    b_n = float(row["breadth_norm"])
    a = float(row["alpha"])
    b = float(row["beta"])
    g = float(row["gamma"])

    core = (
        f"{release_str + ' - ' if release_str else ''}"
        f"{label_str + ' - ' if label_str else ''}"
        f"{_rating_line(review)} - Gesamt: {overall:.3f} "
        f"(Matching-Score: {score:.3f}, "
        f"Abdeckungsquantil eff.: {spec_eff:.3f} "
        f"[roh {spec_raw:.3f} * g={spec_gate:.3f}])"
    )
    meta_html = html.escape(core)

    formula = (
        "alpha*S_a + beta*rating_norm + gamma*Spektrum_eff = "
        f"{a:.3f}*{score:.3f} + {b:.3f}*{rn:.3f} + {g:.3f}*{spec_eff:.3f} "
        f"= {overall:.3f} | purity_norm={p_n:.3f}, breadth_norm={b_n:.3f}, "
        f"Spektrum_roh={spec_raw:.3f}, g(S_a)={spec_gate:.3f}"
    )
    formula_html = html.escape(formula)

    snippet_source = review.text or ""
    snippet = snippet_source[:260] + ("…" if len(snippet_source) > 260 else "")
    snippet_html = html.escape(snippet).replace("\n", "<br>")

    card = '<div class="rec-card">'
    card += f'<div class="rec-header">{rank_html}{header_html}</div>'
    card += f'<div class="rec-meta">{meta_html}</div>'
    card += f'<div class="rec-meta-formula">{formula_html}</div>'
    if top_comms:
        card += _rec_top_communities_html(top_comms)
    else:
        card += (
            '<div class="rec-meta">Keine Stil-Tags für dieses Album '
            "(Zuordnungsdaten fehlen).</div>"
        )
    if snippet_html:
        card += f'<div class="rec-excerpt">{snippet_html}</div>'
    card += "</div>"
    st.markdown(card, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Neueste Rezensionen",
        page_icon=None,
        layout="wide",
    )
    render_toolbar("neueste")
    _newest_css()

    st.markdown(
        '<p class="nw-page-title">Neueste Rezensionen</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="nw-page-desc">Die zuletzt im lokalen Corpus vorhandenen Alben '
        "(nach interner Reihenfolge der Rezensionen; in der Regel "
        "entspricht das den zuletzt auf plattentests.de hinzugekommenen "
        "Rezensionen). Die farbigen Tags zeigen die stärksten "
        "Stil-Zuordnungen (Genre-Label oder Schwerpunkt-Künstler, "
        "sofern vorhanden).</p>",
        unsafe_allow_html=True,
    )

    selected_comms = get_selected_communities()
    if selected_comms:
        st.markdown(
            '<p class="nw-page-desc" style="margin-top:-0.5rem;">'
            "<strong>Präferenzen aktiv</strong> (deine Stil-Auswahl und Gewichte "
            "aus den Filtern): Es werden weiter die <em>neuesten</em> Alben "
            "gezeigt, die <strong>Reihenfolge</strong> entspricht demselben "
            "Gesamtscore wie auf der Seite <strong>Empfehlungen</strong>. "
            "<strong>Serendipity</strong> wird hier <strong>nicht</strong> "
            "genutzt; die Sortierung ist deterministisch. "
            "Das Breiten-Merkmal in der Bewertung bezieht sich auf das "
            "gesamte lokale Rezensionskorpus, nicht nur auf die hier "
            "angezeigte Teilmenge.</p>",
            unsafe_allow_html=True,
        )

    n_show = st.slider(
        "Anzahl Kacheln",
        min_value=5,
        max_value=50,
        value=RECENT_DEFAULT,
    )

    reviews = _load_newest_reviews(n_show)
    ranked_rows: list[dict[str, Any]] | None = None
    if selected_comms:
        filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
        weights_raw: dict[str, float] = (
            st.session_state.get("community_weights_raw") or {}
        )
        aff_map_full = _load_affinity_by_review_id()
        memberships = load_community_memberships()
        weights_key = tuple((str(k), float(v)) for k, v in sorted(weights_raw.items()))
        breadth_norm_global = _cached_global_breadth_norm_map(
            tuple(sorted(selected_comms)),
            weights_key,
        )
        ranked_rows = preference_ranked_rows(
            reviews,
            affinity_by_review_id=aff_map_full,
            memberships=memberships,
            selected_comms=selected_comms,
            weights_raw=weights_raw,
            filter_settings=filter_settings,
            apply_serendipity=False,
            global_breadth_norm_by_review_id=breadth_norm_global or None,
        )
    if not reviews:
        st.warning(
            "Keine Reviews gefunden. Pfad prüfen: `data/reviews.jsonl` "
            "(ggf. Scraping ausführen).",
        )
        return

    aff_map = _load_affinity_top_map(top_k=5)
    genre_labels = load_genre_labels_res_10()
    communities = load_communities_res_10()
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    missing_aff = sum(1 for r in reviews if r.id not in aff_map)
    if missing_aff:
        st.caption(
            "Hinweis: Zu einigen der angezeigten Alben fehlen Zuordnungsdaten "
            "für die Stil-Tags (Datenstand ggf. veraltet)."
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
            _render_newest_scored_card(row, rank, top)
    else:
        for i, review in enumerate(reviews):
            rank = i + 1
            top = _top_communities_display(
                int(review.id),
                aff_map,
                genre_labels,
                comm_by_id,
            )
            _render_newest_chronological_card(review, rank, top)


if __name__ == "__main__":
    main()
