from __future__ import annotations

import html
import json
import random
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl


def _recommendations_css() -> None:
    st.markdown(
        """
        <style>
        .rec-page-title { font-size: 1.6rem; font-weight: 650; letter-spacing: -0.02em; margin-bottom: 0.25rem; }
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
        .rec-header { margin-bottom: 0.35rem; }
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
def _load_communities_res_10() -> list[dict[str, Any]]:
    data_dir = resolve_data_path("data")
    res_name = "10"
    path = Path(data_dir) / f"communities_res_{res_name}.json"
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


def _get_selected_communities() -> set[str]:
    artist_comms = st.session_state.get("artist_flow_selected_communities") or set()
    genre_comms = st.session_state.get("genre_flow_selected_communities") or set()
    artist_set = {str(c) for c in artist_comms}
    genre_set = {str(c) for c in genre_comms}
    return artist_set.union(genre_set)


def _compute_recommendations() -> list[dict[str, Any]]:
    selected_comms = _get_selected_communities()
    if not selected_comms:
        return []

    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = (
        st.session_state.get("community_weights_raw") or {}
    )

    year_min = int(filter_settings.get("year_min", 1990))
    year_max = int(filter_settings.get("year_max", 2030))
    rating_min = float(filter_settings.get("rating_min", 0.0))
    rating_max = float(filter_settings.get("rating_max", 10.0))
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))
    min_hits_pct = float(filter_settings.get("min_hits_pct", 0.0))
    sort_mode = str(filter_settings.get("sort_mode", "Deterministisch"))
    serendipity = float(filter_settings.get("serendipity", 0.0))

    reviews, metadata = _load_reviews_and_metadata()
    affinities = _load_affinities()
    communities = _load_communities_res_10()
    genre_labels = _load_genre_labels_res_10()

    if not reviews or not affinities:
        return []

    review_index: dict[int, Any] = {int(r.id): r for r in reviews}
    comm_by_id: dict[str, dict[str, Any]] = {
        str(c.get("id")): c for c in communities if c.get("id")
    }

    res_key = "res_10"
    total_liked = len(selected_comms) if selected_comms else 1

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

        # Score nur über ausgewählte Communities
        s = 0.0
        k_hits = 0
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
            s += w * val
            if val > 0:
                k_hits += 1

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
        if rating_val is not None:
            if rating_val < rating_min or rating_val > rating_max:
                continue

        year_val: int | None = None
        if review.release_year is not None:
            year_val = review.release_year
        elif review.release_date is not None:
            year_val = review.release_date.year
        if year_val is not None and not (year_min <= year_val <= year_max):
            continue

        hits_pct = 100.0 * k_hits / total_liked
        if hits_pct < min_hits_pct:
            continue

        meta = metadata.get(review_id_val) or {}
        label_list = meta.get("labels") or []
        if not isinstance(label_list, list):
            label_list = []
        label_str = ", ".join(str(l) for l in label_list)

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
                "hits_pct": hits_pct,
                "rating": rating_val,
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

    # Sortierung
    if sort_mode == "Serendipity" and serendipity > 0.0:
        rng = random.Random(42)
        for item in candidates:
            base = float(item["score"])
            noise = rng.random()
            item["serendipity_score"] = (1.0 - serendipity) * base + serendipity * noise
        candidates.sort(key=lambda x: x["serendipity_score"], reverse=True)
    else:
        # Kein Freitext + deterministisch: streng nach Score absteigend.
        # (Wenn später Freitext/RAG hinzukommt, kann hier erweitert werden.)
        candidates.sort(key=lambda x: float(x["score"]), reverse=True)

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
        'Filtereinstellungen und (optional) deiner Stimmungsbeschreibung.</p>',
        unsafe_allow_html=True,
    )

    free_text = (st.session_state.get("free_text_query") or "").strip()
    if free_text:
        st.markdown(f"**Stimmung / Freitext:** `{free_text}`")

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
    selected_comms = _get_selected_communities()
    filter_settings: dict[str, Any] = st.session_state.get("filter_settings") or {}
    weights_raw: dict[str, float] = (
        st.session_state.get("community_weights_raw") or {}
    )

    year_min = int(filter_settings.get("year_min", 1990))
    year_max = int(filter_settings.get("year_max", 2030))
    rating_min = float(filter_settings.get("rating_min", 0.0))
    rating_max = float(filter_settings.get("rating_max", 10.0))
    score_min = float(filter_settings.get("score_min", 0.0))
    score_max = float(filter_settings.get("score_max", 1.0))
    min_hits_pct = float(filter_settings.get("min_hits_pct", 0.0))
    sort_mode = str(filter_settings.get("sort_mode", "Deterministisch"))
    serendipity = float(filter_settings.get("serendipity", 0.0))

    with st.expander("Wie werden die Scores berechnet?", expanded=True):
        st.markdown(
            "- **Formel pro Album**:\n"
            "  `Score = Summe über alle gewählten Communities (Gewicht_c * Affinität_c,Album)`\n"
            "  mit:\n"
            "  - `C_selected`: aktuell gewählte Communities (Artist-/Genre-Flow)\n"
            "  - `Gewicht_c`: Community-Gewicht (Slider in „Filter & Community-Gewichte“)\n"
            "  - `Affinität_c,Album`: Score der Album-Community-Affinität "
            "aus `album_community_affinities.jsonl` für `res_10`.",
        )

        if selected_comms:
            # Normierte Gewichte nur zur Anzeige (Score-Berechnung bleibt bei Roh-Gewichten)
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

        st.markdown(
            "**Zusätzliche Filter, bevor ein Album angezeigt wird:**\n"
            f"- Veröffentlichungsjahr: **{year_min}–{year_max}**\n"
            f"- Rating: **{rating_min:.1f}–{rating_max:.1f}**\n"
            f"- Score-Range: **{score_min:.2f}–{score_max:.2f}**\n"
            f"- Min. Anteil getroffener Communities: **{min_hits_pct:.0f}%**\n"
            f"- Sortierung: **{sort_mode}**"
            f"{' (Serendipity=' + str(serendipity) + ')' if sort_mode == 'Serendipity' else ''}",
        )

    st.markdown(f"**{len(recs)} Alben entsprechen aktuell deinen Kriterien.**")

    # Kachel-Darstellung
    num_cols = 3
    cols = st.columns(num_cols)
    for idx, rec in enumerate(recs):
        col = cols[idx % num_cols]
        with col:
            artist = rec.get("artist") or ""
            album = rec.get("album") or ""
            url = rec.get("url") or ""
            rating = rec.get("rating")
            year = rec.get("year")
            labels = rec.get("labels") or ""
            score = float(rec.get("score") or 0.0)
            hits_pct = float(rec.get("hits_pct") or 0.0)
            top_comms = rec.get("top_communities") or []
            text = rec.get("text") or ""
            snippet = text[:260] + ("…" if len(text) > 260 else "")

            # Überschrift: Artist – Album
            header = f"{html.escape(str(artist))} — {html.escape(str(album))}"
            if url:
                link_attrs = (
                    f'href="{html.escape(url)}" target="_blank" rel="noopener"'
                )
                header_html = (
                    f'<a {link_attrs} class="rec-title">{header}</a>'
                )
            else:
                header_html = f'<span class="rec-title">{header}</span>'

            # Meta-Zeile: Veröffentlichungsdatum – Label – Rating – Score – Treffer%
            meta_parts: list[str] = []
            release_str = ""
            if rec.get("release_date"):
                release_str = rec["release_date"].strftime("%d.%m.%Y")
            elif year is not None:
                release_str = str(year)
            if release_str:
                meta_parts.append(release_str)
            if labels:
                meta_parts.append(labels)
            if rating is not None:
                meta_parts.append(f"{int(rating)}/10")
            meta_parts.append(f"Score: {score:.3f}")
            meta_parts.append(f"Abdeckung ausgewählter Genres: {hits_pct:.0f}%")
            meta_html = " – ".join(html.escape(str(p)) for p in meta_parts)

            snippet_html = html.escape(snippet).replace("\n", "<br>")

            card = '<div class="rec-card">'
            card += f'<div class="rec-header">{header_html}</div>'
            if meta_html:
                card += f'<div class="rec-meta">{meta_html}</div>'
            # Top-Communities als Tags mit farbcodierter „Stärke“-Visualisierung
            if top_comms:
                card += '<div class="rec-communities">'
                for tc in top_comms:
                    label = str(tc.get("label") or "")
                    aff = float(tc.get("affinity") or 0.0)
                    # Farbskala: schwach = hellgrau, stark = kräftig blaugrün
                    if aff >= 0.6:
                        bg = "#0f766e"   # kräftiges Teal
                        border = "#0f766e"
                        fg = "#ecfeff"
                        bars = "▮▮▮"
                    elif aff >= 0.3:
                        bg = "#22c55e"   # grün
                        border = "#16a34a"
                        fg = "#ecfdf3"
                        bars = "▮▮"
                    elif aff >= 0.1:
                        bg = "#e0f2fe"   # hellblau
                        border = "#93c5fd"
                        fg = "#0f172a"
                        bars = "▮"
                    else:
                        bg = "#f3f4f6"   # sehr schwach
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

    st.markdown("---")
    col_back, col_start = st.columns([1, 1])
    with col_back:
        if st.button("Filter anpassen"):
            st.switch_page("pages/5_Filter_Flow.py")
    with col_start:
        if st.button("Neuer Flow starten"):
            st.switch_page("streamlit_app.py")


if __name__ == "__main__":
    main()

