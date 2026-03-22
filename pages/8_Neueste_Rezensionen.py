"""Neueste Rezensionen aus dem lokalen Corpus mit Community-/Genre-Tags."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env
from music_review.config import resolve_data_path
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
        .nw-card {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .nw-card:hover {
            border-color: #d1d5db;
            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.06);
        }
        .nw-header { margin-bottom: 0.35rem; }
        .nw-title {
            font-size: 1.05rem;
            font-weight: 600;
            text-decoration: none;
            color: #111827;
        }
        .nw-title:hover { text-decoration: underline; color: #1d4ed8; }
        .nw-meta {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 0.40rem;
        }
        .nw-communities {
            font-size: 0.78rem;
            color: #4b5563;
            margin-bottom: 0.35rem;
        }
        .nw-comm-tag {
            display: inline-flex;
            align-items: center;
            padding: 0.10rem 0.45rem;
            margin: 0 0.25rem 0.25rem 0;
            border-radius: 999px;
            border: 1px solid transparent;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .nw-excerpt {
            font-size: 0.86rem;
            line-height: 1.5;
            color: #4b5563;
        }
        .nw-comm-h {
            font-size: 0.72rem;
            font-weight: 650;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #64748b;
            margin: 0.35rem 0 0.25rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_release_date(value: Any, release_year: Any) -> str:
    if value is not None:
        if hasattr(value, "strftime"):
            try:
                return value.strftime("%d.%m.%Y")
            except Exception:
                pass
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime("%d.%m.%Y")
            except ValueError:
                pass
    if release_year is not None:
        try:
            return str(int(release_year))
        except (TypeError, ValueError):
            pass
    return ""


@st.cache_data(ttl=3600)
def _load_communities_res_10() -> list[dict[str, Any]]:
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "communities_res_10.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    comms = data.get("communities")
    if not isinstance(comms, list):
        return []
    return [c for c in comms if isinstance(c, dict) and c.get("id")]


@st.cache_data(ttl=3600)
def _load_genre_labels_res_10() -> dict[str, str]:
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "community_genre_labels_res_10.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return {}
    mapping: dict[str, str] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        label = item.get("genre_label")
        if cid is None or not label:
            continue
        mapping[str(cid)] = str(label)
    return mapping


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


def _top_communities_display(
    review_id: int,
    aff_map: dict[int, list[tuple[str, float]]],
    genre_labels: dict[str, str],
    comm_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cid, aff in aff_map.get(review_id, []):
        label = genre_labels.get(cid)
        c_obj = comm_by_id.get(cid)
        if not label and isinstance(c_obj, dict):
            centroid = c_obj.get("centroid")
            if centroid:
                label = str(centroid)
        if not label:
            label = f"Community {cid}"
        out.append({"id": cid, "label": label, "affinity": aff})
    return out


def _comm_tag_style(aff: float) -> tuple[str, str, str, str]:
    if aff >= 0.6:
        return "#0f766e", "#0f766e", "#ecfeff", "▮▮▮"
    if aff >= 0.3:
        return "#22c55e", "#16a34a", "#ecfdf3", "▮▮"
    if aff >= 0.1:
        return "#e0f2fe", "#93c5fd", "#0f172a", "▮"
    return "#f3f4f6", "#e5e7eb", "#4b5563", ""


def _render_card(review: Review, top_comms: list[dict[str, Any]]) -> None:
    artist = review.artist or ""
    album = review.album or ""
    url = review.url or ""
    rid = int(review.id)
    header = f"{html.escape(str(artist))} — {html.escape(str(album))}"
    if url:
        link = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
        header_html = f'<a {link} class="nw-title">{header}</a>'
    else:
        header_html = f'<span class="nw-title">{header}</span>'

    label_list = review.labels or []
    label_str = ", ".join(str(x) for x in label_list) if label_list else ""
    rel = _format_release_date(review.release_date, review.release_year)
    meta_parts: list[str] = [f"Rezensions-ID **{rid}**"]
    if rel:
        meta_parts.append(rel)
    if label_str:
        meta_parts.append(label_str)
    if review.rating is not None:
        meta_parts.append(f"{int(review.rating)}/10")
    meta_html = " · ".join(meta_parts)

    text = (review.text or "")[:280]
    snippet = html.escape(text).replace("\n", "<br>")
    if len(review.text or "") > 280:
        snippet += "…"

    card = '<div class="nw-card">'
    card += f'<div class="nw-header">{header_html}</div>'
    card += f'<div class="nw-meta">{meta_html}</div>'
    card += '<div class="nw-comm-h">Communities (Graph, res_10) / Genre-Labels</div>'
    if top_comms:
        card += '<div class="nw-communities">'
        for tc in top_comms:
            aff = float(tc.get("affinity") or 0.0)
            lab = str(tc.get("label") or "")
            bg, border, fg, bars = _comm_tag_style(aff)
            tag_text = lab + (f" {bars}" if bars else "")
            card += (
                f'<span class="nw-comm-tag" '
                f'style="background-color:{bg};border-color:{border};color:{fg};">'
                f"{html.escape(tag_text)}"
                "</span>"
            )
        card += "</div>"
    else:
        card += (
            '<div class="nw-meta">Keine Eintraege in '
            "<code>album_community_affinities.jsonl</code> fuer diese ID.</div>"
        )
    if snippet:
        card += f'<div class="nw-excerpt">{snippet}</div>'
    card += "</div>"
    st.markdown(card, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Neueste Rezensionen",
        page_icon="🆕",
        layout="wide",
    )
    _newest_css()

    st.markdown(
        '<p class="nw-page-title">Neueste Rezensionen</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="nw-page-desc">Die zuletzt im lokalen Corpus vorhandenen Alben '
        "(nach <strong>Rezensions-ID</strong>, absteigend — entspricht in der "
        "Regel den zuletzt auf plattentests.de hinzugekommenen Rezensionen). "
        "Die farbigen Tags zeigen die staerksten Community-Zuordnungen "
        "(Aufloesung <code>res_10</code>) mit Genre-Label wo vorhanden.</p>",
        unsafe_allow_html=True,
    )

    n_show = st.slider(
        "Anzahl Kacheln",
        min_value=5,
        max_value=50,
        value=RECENT_DEFAULT,
    )

    reviews = _load_newest_reviews(n_show)
    if not reviews:
        st.warning(
            "Keine Reviews gefunden. Pfad pruefen: `data/reviews.jsonl` "
            "(ggf. Scraping ausfuehren).",
        )
        return

    aff_map = _load_affinity_top_map(top_k=5)
    genre_labels = _load_genre_labels_res_10()
    communities = _load_communities_res_10()
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    missing_aff = sum(1 for r in reviews if r.id not in aff_map)
    if missing_aff:
        st.caption(
            f"Hinweis: Bei **{missing_aff}** der angezeigten IDs fehlen "
            "Graph-Affinitaeten (Datei veraltet oder noch nicht neu berechnet)."
        )

    c1, c2 = st.columns(2, gap="large")
    for i, review in enumerate(reviews):
        col = c1 if i % 2 == 0 else c2
        with col:
            top = _top_communities_display(
                int(review.id),
                aff_map,
                genre_labels,
                comm_by_id,
            )
            _render_card(review, top)


if __name__ == "__main__":
    main()
