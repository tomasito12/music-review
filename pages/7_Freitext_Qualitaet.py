"""Diagnose: semantische Freitext-Suche vs. Volltext und Filter-Schnittmenge."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import streamlit as st

from music_review.config import resolve_data_path
from music_review.io.jsonl import iter_jsonl_objects
from music_review.pipeline.retrieval.vector_store import (
    CHUNK_COLLECTION_NAME,
    COLLECTION_NAME,
    generate_query_variants,
    search_reviews,
    search_reviews_with_variants,
    semantic_distance_map_for_review_ids,
)

KEY_FORM = "freitext_qualitaet_form"
KEY_CLEAR = "freitext_qualitaet_clear"


def _reviews_path() -> Path:
    return resolve_data_path("data/reviews.jsonl")


def _lexical_count_corpus(needle: str, *, max_lines: int | None = None) -> int:
    """Count reviews whose text contains needle (case-insensitive)."""
    path = _reviews_path()
    if not path.is_file():
        return -1
    n = 0
    lines = 0
    needle_l = needle.strip().lower()
    if not needle_l:
        return 0
    for obj in iter_jsonl_objects(path, log_errors=False):
        lines += 1
        if max_lines is not None and lines > max_lines:
            break
        if not isinstance(obj, dict):
            continue
        text = str(obj.get("text") or "").lower()
        if needle_l in text:
            n += 1
    return n


def _load_texts_for_ids(review_ids: set[int]) -> dict[int, str]:
    """One pass over reviews.jsonl; keep text for requested ids."""
    path = _reviews_path()
    out: dict[int, str] = {}
    if not path.is_file() or not review_ids:
        return out
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        rid = obj.get("id")
        if not isinstance(rid, int):
            try:
                rid = int(rid) if rid is not None else None
            except (TypeError, ValueError):
                rid = None
        if rid is None or rid not in review_ids:
            continue
        out[rid] = str(obj.get("text") or "").lower()
    return out


def _parse_id_list(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.add(int(p))
        except ValueError:
            continue
    return out


def _distance_bins(dists: list[float]) -> list[tuple[str, int]]:
    edges = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 10.0)]
    labels: list[tuple[str, int]] = []
    for lo, hi in edges:
        c = sum(1 for d in dists if lo <= d < hi)
        labels.append((f"{lo}-{hi}", c))
    return labels


def _substring_reviews_from_jsonl(needle: str) -> list[tuple[int, str, str, str]]:
    """All reviews where `text` contains needle (case-insensitive)."""
    needle_l = needle.strip().lower()
    path = _reviews_path()
    if not needle_l or not path.is_file():
        return []
    out: list[tuple[int, str, str, str]] = []
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        text = str(obj.get("text") or "").lower()
        if needle_l not in text:
            continue
        rid_raw = obj.get("id")
        if not isinstance(rid_raw, int):
            try:
                rid_raw = int(rid_raw) if rid_raw is not None else None
            except (TypeError, ValueError):
                rid_raw = None
        if rid_raw is None:
            continue
        artist = str(obj.get("artist") or "")
        album = str(obj.get("album") or "")
        url = str(obj.get("url") or "")
        out.append((rid_raw, artist, album, url))
    return out


def _distance_by_review_id(hits: list[Any]) -> dict[int, float]:
    """Best (smallest) semantic distance per review_id from fusion hits."""
    best: dict[int, float] = {}
    for h in hits:
        rid = h.get("review_id")
        dist = h.get("distance")
        if not isinstance(rid, int) or not isinstance(dist, (int, float)):
            continue
        d = float(dist)
        if rid not in best or d < best[rid]:
            best[rid] = d
    return best


def _render_stored_results() -> None:
    hits = st.session_state.get("freitext_debug_hits")
    params = st.session_state.get("freitext_debug_params")
    variant_stats = st.session_state.get("freitext_debug_variants_stats") or []
    if not isinstance(hits, list) or not isinstance(params, dict):
        return

    max_dist = float(params.get("max_dist", 1.0))
    q = str(params.get("query", ""))
    variants_len = int(params.get("variants_len", 0))
    filter_ids_raw = str(params.get("filter_ids_raw", ""))

    dists = [
        float(h["distance"])
        for h in hits
        if isinstance(h.get("distance"), (int, float))
    ]
    under = sum(1 for d in dists if d <= max_dist)

    st.subheader("Ueberblick (letzte Suche)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Reviews nach Fusion", len(hits))
    m2.metric(f"Distanz <= {max_dist:.2f}", under)
    if dists:
        med = sorted(dists)[len(dists) // 2]
        dist_label = f"{min(dists):.3f} / {med:.3f} / {max(dists):.3f}"
    else:
        dist_label = "—"
    m3.metric("Min. / Med. / Max. Distanz", dist_label)
    m4.metric("Query-Varianten", variants_len)

    fid = _parse_id_list(filter_ids_raw)
    if fid:
        in_filter = [
            h
            for h in hits
            if isinstance(h.get("review_id"), int) and int(h["review_id"]) in fid
        ]
        under_f = [
            h
            for h in in_filter
            if isinstance(h.get("distance"), (int, float))
            and float(h["distance"]) <= max_dist
        ]
        st.markdown(
            f"**Mit deiner ID-Liste ({len(fid)} IDs):** "
            f"{len(in_filter)} Treffer in der Fusion-Liste, "
            f"davon **{len(under_f)}** mit Distanz <= {max_dist:.2f}.",
        )

    lc = st.session_state.get("freitext_debug_lexical_count")
    lit = st.session_state.get("freitext_debug_lexical_in_top")
    top_n_lex = st.session_state.get("freitext_debug_lexical_top_n")
    if isinstance(lc, int) and lc >= 0:
        top_n_disp = (
            int(top_n_lex) if isinstance(top_n_lex, int) else min(200, len(hits))
        )
        st.markdown("**Volltext-Substring** (case-insensitive, im Feld `text`):")
        st.markdown(
            f"- **Gesamt in `reviews.jsonl`:** **{lc}** Rezensionen mit diesem "
            "Substring im Volltext.\n"
            f"- **In den ersten {top_n_disp} Eintraegen der semantischen Liste:** "
            f"**{lit}** mit Substring im Volltext (Vergleich Embedding vs. Text)."
            if isinstance(lit, int)
            else (
                f"- **Gesamt in `reviews.jsonl`:** **{lc}** Rezensionen.\n"
                "- **Top-N-Vergleich:** Suche erneut mit Haekchen "
                "'Volltext zaehlen' aktivieren."
            )
        )

    st.subheader("Distanz-Verteilung")
    if dists:
        for label, cnt in _distance_bins(dists):
            st.write(f"{label}: **{cnt}**")

    with st.expander("Query-Varianten und Chroma-Roh-Treffer pro Variante"):
        st.dataframe(variant_stats, use_container_width=True, hide_index=True)

    st.subheader("Top-Treffer")
    rows: list[dict[str, Any]] = []
    for i, h in enumerate(hits[:80], start=1):
        rid = h.get("review_id")
        dist = h.get("distance")
        chunk = str(h.get("chunk_text") or "")
        snippet = str(h.get("chunk_text") or h.get("text") or "")[:220]
        dist_r = round(float(dist), 4) if isinstance(dist, (int, float)) else None
        under_t = isinstance(dist, (int, float)) and float(dist) <= max_dist
        rows.append(
            {
                "rank": i,
                "review_id": rid,
                "distance": dist_r,
                "under_thresh": under_t,
                "artist": h.get("artist"),
                "album": h.get("album"),
                "snippet": snippet + ("..." if len(chunk) > 220 else ""),
                "url": h.get("url"),
            },
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"Gespeicherte Abfrage: {q!r}")

    q_strip = str(params.get("query", "")).strip()
    if q_strip:
        st.subheader("Reviews mit Substring im Volltext (`reviews.jsonl`)")
        st.caption(
            "**semantische_distanz:** L2-Abstand zwischen **einem** Embedding der "
            "Original-Query und allen gespeicherten Vektoren des Reviews (bei Chunks: "
            "Minimum ueber Chunks). Benoetigt `OPENAI_API_KEY` und den gewaehlten "
            "Chroma-Index. **distanz_fusion:** beste Distanz aus der Fusion-Liste "
            "(mehrere Query-Varianten) — kann von der ersten Spalte abweichen.",
        )
        with st.spinner("Durchlaufe reviews.jsonl nach Substring …"):
            lexical_rows = _substring_reviews_from_jsonl(q_strip)

        collection_used = str(params.get("collection") or COLLECTION_NAME)
        rids = [r[0] for r in lexical_rows]
        sig: tuple[str, str, tuple[int, ...]] = (
            q_strip,
            collection_used,
            tuple(sorted(set(rids))),
        )
        dist_fusion = _distance_by_review_id(hits)

        comp_dist: dict[int, float | None] = {}
        if rids:
            cached_sig = st.session_state.get("freitext_debug_subdist_sig")
            cached_map = st.session_state.get("freitext_debug_subdist_map")
            if cached_sig == sig and isinstance(cached_map, dict):
                comp_dist = cast(dict[int, float | None], cached_map)
            else:
                try:
                    with st.spinner(
                        "Berechne semantische Distanzen (OpenAI + Chroma) …",
                    ):
                        comp_dist = semantic_distance_map_for_review_ids(
                            q_strip,
                            rids,
                            collection_name=collection_used,
                        )
                except RuntimeError as err:
                    if "OPENAI_API_KEY" in str(err):
                        st.error("OPENAI_API_KEY fehlt fuer Embedding der Suchanfrage.")
                    else:
                        st.error(f"Distanzberechnung: {err}")
                    comp_dist = {}
                except Exception as err:
                    st.error(f"Distanzberechnung: {err}")
                    comp_dist = {}
                else:
                    st.session_state["freitext_debug_subdist_sig"] = sig
                    st.session_state["freitext_debug_subdist_map"] = comp_dist

        rows_all: list[dict[str, Any]] = []
        for rid, artist, album, url in lexical_rows:
            cd = comp_dist.get(rid) if comp_dist else None
            fd = dist_fusion.get(rid)
            rows_all.append(
                {
                    "review_id": rid,
                    "artist": artist,
                    "album": album,
                    "url": url,
                    "semantische_distanz": round(float(cd), 4)
                    if isinstance(cd, (int, float))
                    else None,
                    "distanz_fusion": round(float(fd), 4)
                    if isinstance(fd, (int, float))
                    else None,
                },
            )

        def _sort_key(r: dict[str, Any]) -> tuple[bool, float]:
            sd = r.get("semantische_distanz")
            if isinstance(sd, (int, float)):
                return (False, float(sd))
            return (True, 999.0)

        rows_all.sort(key=_sort_key)

        n_with_vec = sum(
            1
            for r in rows_all
            if isinstance(r.get("semantische_distanz"), (int, float))
        )
        n_no_index = len(rows_all) - n_with_vec
        n_in_fusion = sum(
            1 for r in rows_all if isinstance(r.get("distanz_fusion"), (int, float))
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Substring gesamt", len(lexical_rows))
        c2.metric("mit semantischer Distanz", n_with_vec)
        c3.metric("nicht im Chroma-Index", n_no_index)
        c4.metric("auch in Fusion-Liste", n_in_fusion)

        cap = 800
        st.markdown(
            f"**Alle Substring-Treffer** (sortiert nach `semantische_distanz`, "
            f"max. {cap} Zeilen)",
        )
        st.dataframe(rows_all[:cap], use_container_width=True, hide_index=True)
        if len(rows_all) > cap:
            st.caption(f"… und {len(rows_all) - cap} weitere Zeilen nicht angezeigt.")


def main() -> None:
    st.set_page_config(
        page_title="Music Review — Freitext-Qualitaet",
        page_icon=None,
        layout="wide",
    )

    st.title("Freitext-Qualitaet / RAG-Diagnose")
    st.markdown(
        """
Diese Seite hilft zu verstehen, **warum** die semantische Suche auf der
Empfehlungsseite oft **weniger Treffer** liefert, als du bei haeufigen
Woertern im Volltext erwarten wuerdest.

**Wichtig:**

1. **Embeddings sind nicht Volltextsuche.** Aehnlichkeit ist Naehe im
   Embedding-Raum. Ein Wort kann oft vorkommen, aber **schlecht ranken**.
2. **Nur Top-K aus der ganzen Datenbank.** Pro Query-Variante nur
   `top_k` Chroma-Treffer; nach Fusion maximal `n_results` Reviews.
   Alben **ausserhalb** dieser Liste erscheinen nicht.
3. **Empfehlungsseite zusaetzlich:** Schnittmenge mit gefilterten Alben
   **und** Schwelle **Max. Distanz**.

**„Chat zuruecksetzen“** leert nur den Freitext im Tab, nicht den Index.
        """
    )

    if st.button("Gespeicherte Debug-Ergebnisse leeren", key=KEY_CLEAR):
        for k in (
            "freitext_debug_hits",
            "freitext_debug_params",
            "freitext_debug_variants_stats",
            "freitext_debug_lexical_count",
            "freitext_debug_lexical_in_top",
            "freitext_debug_lexical_top_n",
            "freitext_debug_subdist_sig",
            "freitext_debug_subdist_map",
        ):
            st.session_state.pop(k, None)
        st.rerun()

    with st.form(KEY_FORM):
        query = st.text_input(
            "Suchbegriff / Freitext",
            placeholder="z. B. melancholisch, traurig, gluecklich",
        )
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            strategy = st.selectbox("RAG-Variante", ["A", "B", "C"], index=1)
        with col_b:
            top_k = st.slider("Top-K pro Query-Variante (Chroma)", 10, 120, 30)
        with col_c:
            n_fused = st.slider("Max. Reviews nach Fusion", 50, 400, 200)

        collection = st.radio(
            "Chroma-Collection",
            (CHUNK_COLLECTION_NAME, COLLECTION_NAME),
            format_func=lambda x: (
                "Chunks (v1)"
                if x == CHUNK_COLLECTION_NAME
                else "Ganze Reviews (legacy)"
            ),
            horizontal=True,
        )

        max_dist = st.slider(
            "Distanz-Schwelle (wie Empfehlungsseite, nur Auswertung)",
            0.0,
            2.0,
            1.0,
            0.05,
        )

        filter_ids_raw = st.text_area(
            "Optional: Review-IDs fuer Schnittmenge (Komma-getrennt)",
            placeholder="z. B. 1234, 5678 — leer = keine Schnittmenge",
            height=68,
        )

        do_lexical = st.checkbox(
            "Volltext zaehlen in reviews.jsonl (ein Durchlauf, kann dauern)",
            value=False,
        )

        submitted = st.form_submit_button("Suche ausfuehren", type="primary")

    if submitted:
        q = (query or "").strip()
        if not q:
            st.warning("Bitte einen Suchbegriff eingeben.")
        else:
            try:
                with st.spinner("Chroma-Abfrage laeuft ..."):
                    hits = search_reviews_with_variants(
                        q,
                        strategy=strategy,
                        n_results=int(n_fused),
                        top_k_per_variant=int(top_k),
                        where=None,
                        collection_name=collection,
                    )
            except RuntimeError as err:
                if "OPENAI_API_KEY" in str(err):
                    st.error("OPENAI_API_KEY fehlt (.env / Umgebung).")
                else:
                    st.error(f"Fehler: {err}")
            except Exception as err:
                st.error(f"Fehler: {err}")
            else:
                variants = generate_query_variants(q, strategy=strategy, max_variants=8)
                variant_stats: list[dict[str, Any]] = []
                for v in variants:
                    try:
                        vh = search_reviews(
                            v,
                            n_results=int(top_k),
                            where=None,
                            collection_name=collection,
                        )
                        dists_v = [
                            float(h["distance"])
                            for h in vh
                            if isinstance(h.get("distance"), (int, float))
                        ]
                        short = v[:120] + ("..." if len(v) > 120 else "")
                        variant_stats.append(
                            {
                                "variant": short,
                                "chunks": len(vh),
                                "min_dist": min(dists_v) if dists_v else None,
                            },
                        )
                    except Exception:
                        variant_stats.append(
                            {
                                "variant": v[:120],
                                "chunks": 0,
                                "min_dist": None,
                            },
                        )

                st.session_state["freitext_debug_hits"] = hits
                st.session_state["freitext_debug_params"] = {
                    "query": q,
                    "strategy": strategy,
                    "top_k": top_k,
                    "n_fused": n_fused,
                    "collection": collection,
                    "max_dist": max_dist,
                    "filter_ids_raw": filter_ids_raw,
                    "variants_len": len(variants),
                }
                st.session_state["freitext_debug_variants_stats"] = variant_stats
                st.session_state.pop("freitext_debug_lexical_count", None)
                st.session_state.pop("freitext_debug_lexical_in_top", None)
                st.session_state.pop("freitext_debug_lexical_top_n", None)

                if do_lexical:
                    with st.spinner("Volltext zaehlen ..."):
                        lc = _lexical_count_corpus(q, max_lines=None)
                    st.session_state["freitext_debug_lexical_count"] = lc
                    if lc >= 0:
                        top_n_slice = min(200, len(hits))
                        st.session_state["freitext_debug_lexical_top_n"] = top_n_slice
                        top_ids = {
                            int(h["review_id"])
                            for h in hits[:top_n_slice]
                            if isinstance(h.get("review_id"), int)
                        }
                        texts = _load_texts_for_ids(top_ids)
                        qlow = q.strip().lower()
                        lexical_in_top = sum(
                            1 for rid in top_ids if qlow and qlow in texts.get(rid, "")
                        )
                        st.session_state["freitext_debug_lexical_in_top"] = (
                            lexical_in_top
                        )

                st.rerun()

    if st.session_state.get("freitext_debug_hits") is not None:
        _render_stored_results()


if __name__ == "__main__":
    main()
