#!/usr/bin/env python3
"""Streamlit dashboard to browse music reviews and metadata."""

from __future__ import annotations

import html
import json
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.pipeline.retrieval.vector_store import search_reviews

DEBUG_LOG_PATH = Path(
    "/Users/plischke/Desktop/Private Development/music-review/.cursor/debug-949f78.log",
)


def _debug_log(
    run_id: str,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
) -> None:
    """Append a single NDJSON debug log line (for agent debugging only)."""
    try:
        payload = {
            "sessionId": "949f78",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        # #region agent log
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        # #endregion
    except Exception:
        # Never let logging break the app.
        pass


def load_data() -> tuple[list, dict[int, dict]]:
    """Load reviews and metadata; return (reviews_list, metadata_by_review_id)."""
    reviews_path = resolve_data_path("data/reviews.jsonl")
    # Prefer imputed metadata (includes same-artist and reference imputation)
    imputed_path = resolve_data_path("data/metadata_imputed.jsonl")
    fallback_path = resolve_data_path("data/metadata.jsonl")
    metadata_path = imputed_path if imputed_path.exists() else fallback_path

    if not reviews_path.exists():
        return [], {}

    reviews = load_reviews_from_jsonl(reviews_path)
    metadata_map: dict[int, dict] = {}
    if metadata_path.exists():
        metadata_map = load_jsonl_as_map(
            metadata_path,
            id_key="review_id",
            log_errors=False,
        )
    return reviews, metadata_map


def build_records(
    reviews: list,
    metadata_map: dict[int, dict],
) -> list[dict[str, Any]]:
    """Flatten reviews and metadata into simple records for summaries."""
    records: list[dict[str, Any]] = []
    for r in reviews:
        meta = metadata_map.get(r.id, {})
        if not isinstance(meta, dict):
            meta = {}
        genres = meta.get("genres") or []
        if not isinstance(genres, list):
            genres = []

        year: int | None = None
        if r.release_year is not None:
            year = r.release_year
        elif r.release_date is not None:
            year = r.release_date.year

        records.append(
            {
                "id": r.id,
                "artist": r.artist,
                "album": r.album,
                "author": r.author,
                "rating": r.rating,
                "user_rating": r.user_rating,
                "year": year,
                "genres": genres,
                "genres_inferred_from_artist": bool(
                    meta.get("genres_inferred_from_artist"),
                ),
                "genres_inferred_from_references": bool(
                    meta.get("genres_inferred_from_references"),
                ),
            },
        )
    return records


def render_browse_page(
    reviews: list,
    metadata_map: dict[int, dict],
) -> None:
    """Main browse page: artist/album selection and full review."""
    # Persist selection across reruns so "Random" can set it
    if "selected_artist" not in st.session_state:
        st.session_state["selected_artist"] = reviews[0].artist
    if "selected_album" not in st.session_state:
        st.session_state["selected_album"] = reviews[0].album

    # Compact filter row: Artist, Album, Random button (not full width)
    artists = sorted({r.artist for r in reviews}, key=str.lower)
    artist_index = (
        artists.index(st.session_state["selected_artist"])
        if st.session_state["selected_artist"] in artists
        else 0
    )

    col_artist, col_album, col_btn = st.columns([2, 2, 1])
    with col_artist:
        artist = st.selectbox(
            "Artist",
            options=artists,
            index=artist_index,
            placeholder="Choose artist…",
        )
    st.session_state["selected_artist"] = artist
    if not artist:
        return

    albums_for_artist = sorted(
        {r.album for r in reviews if r.artist == artist},
        key=str.lower,
    )
    with col_album:
        album_index = (
            albums_for_artist.index(st.session_state["selected_album"])
            if st.session_state["selected_album"] in albums_for_artist
            else 0
        )
        album = st.selectbox(
            "Album",
            options=albums_for_artist,
            index=album_index,
            placeholder="Choose album…",
        )
    st.session_state["selected_album"] = album
    with col_btn:
        st.write("")  # align button with selectboxes
        if st.button("🎲 Random"):
            r = random.choice(reviews)
            st.session_state["selected_artist"] = r.artist
            st.session_state["selected_album"] = r.album
            st.rerun()
    if not album:
        return

    # Find review(s) for this artist/album (take first if multiple)
    matching = [r for r in reviews if r.artist == artist and r.album == album]
    review = matching[0] if matching else None
    if not review:
        st.info("No review found for this selection.")
        return

    meta = metadata_map.get(review.id)

    # Header: link, title
    st.markdown(f"[Review #{review.id}]({review.url}) on plattentests.de")
    if review.title:
        st.markdown(f"*{review.title}*")

    # Prominent: rating and release
    rate_col, release_col, _ = st.columns([1, 1, 2])
    with rate_col:
        if review.rating is not None:
            st.metric("Rating", f"{review.rating:.1f}", "out of 10")
        if review.user_rating is not None:
            st.caption(f"User average: {review.user_rating:.1f}/10")
    with release_col:
        if review.release_date:
            st.markdown("**Release**")
            st.markdown(f"{review.release_date.strftime('%d %B %Y')}")
        elif review.release_year is not None:
            st.markdown("**Release year**")
            st.markdown(f"{review.release_year}")
        else:
            st.markdown("**Release**")
            st.caption("—")

    # Rest of metadata in one line
    other_parts: list[str] = []
    if review.author:
        other_parts.append(f"Author: {review.author}")
    if review.labels:
        other_parts.append("Labels: " + ", ".join(review.labels))
    if review.total_duration:
        other_parts.append(f"Duration: {review.total_duration}")
    if other_parts:
        st.caption(" · ".join(other_parts))

    if review.tracklist:
        with st.expander("Tracklist", expanded=False):
            for t in review.tracklist:
                highlight = " ⭐" if t.is_highlight else ""
                st.text(f"{t.number}. {t.title}{highlight}")
        if review.highlights:
            st.caption("Highlights: " + ", ".join(review.highlights))

    st.divider()

    # Two columns: review text (2/3), side column with Referenzen + MusicBrainz (1/3)
    col_review, col_side = st.columns([2, 1])
    with col_review:
        st.markdown(review.text)
        st.divider()
        st.caption(f"**{review.artist}** — *{review.album}* (ID: {review.id})")

    with col_side:
        if review.references:
            with st.expander("Referenzen", expanded=False):
                st.write(", ".join(review.references))
        if meta:
            with st.expander("MusicBrainz metadata", expanded=False):
                if meta.get("genres"):
                    st.markdown("**Genres:** " + ", ".join(meta["genres"]))
                    if meta.get("genres_inferred_from_references"):
                        refs = meta.get("reference_artists_used", [])
                        st.caption(f"From references: {', '.join(refs)}")
                    elif meta.get("genres_inferred_from_artist"):
                        st.caption("From same-artist profile")
                if meta.get("mbid"):
                    st.caption(f"Release MBID: {meta['mbid']}")
                if meta.get("artist_mbid"):
                    st.caption(f"Artist MBID: {meta['artist_mbid']}")
                if meta.get("artist_country"):
                    st.caption(f"Artist country: {meta['artist_country']}")
                if meta.get("artist_type"):
                    st.caption(f"Artist type: {meta['artist_type']}")
                if meta.get("raw_tags"):
                    st.caption("Raw tags: " + ", ".join(meta["raw_tags"]))


def render_genres_page(records: list[dict[str, Any]]) -> None:
    """Overview by genre: filters + per-genre counts and album table."""
    all_genres: set[str] = set()
    years: list[int] = []
    ratings: list[float] = []
    for rec in records:
        for g in rec["genres"]:
            all_genres.add(str(g))
        if rec["year"] is not None:
            years.append(rec["year"])
        if rec["rating"] is not None:
            ratings.append(rec["rating"])

    st.subheader("Genres overview")
    selected_genres = st.multiselect(
        "Filter by genre",
        options=sorted(all_genres),
    )

    year_range: tuple[int, int] | None = None
    if years:
        min_year, max_year = min(years), max(years)
        year_range = st.slider(
            "Filter by release year",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
        )

    min_rating: float | None = None
    if ratings:
        min_rating = st.slider(
            "Minimum rating",
            min_value=float(int(min(ratings))),
            max_value=float(int(max(ratings))),
            value=float(int(min(ratings))),
        )

    def _matches_filters(rec: dict[str, Any]) -> bool:
        if selected_genres and not any(g in selected_genres for g in rec["genres"]):
            return False
        if (
            year_range
            and rec["year"] is not None
            and not (year_range[0] <= rec["year"] <= year_range[1])
        ):
            return False
        return not (
            min_rating is not None
            and rec["rating"] is not None
            and rec["rating"] < min_rating
        )

    filtered = [rec for rec in records if _matches_filters(rec)]

    genre_counts: Counter[str] = Counter()
    for rec in filtered:
        for g in rec["genres"]:
            genre_counts[str(g)] += 1

    genre_rows = [
        {"genre": genre, "albums": count} for genre, count in genre_counts.most_common()
    ]
    st.markdown("**Genre counts (filtered)**")
    st.dataframe(genre_rows, use_container_width=True)

    album_rows: list[dict[str, Any]] = []
    for rec in filtered:
        album_rows.append(
            {
                "artist": rec["artist"],
                "album": rec["album"],
                "year": rec["year"],
                "rating": rec["rating"],
                "genres": ", ".join(str(g) for g in rec["genres"]),
            },
        )
    st.markdown("**Albums (filtered)**")
    st.dataframe(album_rows, use_container_width=True)


def render_artists_page(records: list[dict[str, Any]]) -> None:
    """Overview by artist: album counts, ratings, and main genres."""
    st.subheader("Artists overview")

    by_artist: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_artist.setdefault(rec["artist"], []).append(rec)

    min_albums = st.slider(
        "Minimum albums per artist",
        min_value=1,
        max_value=max(len(v) for v in by_artist.values()),
        value=1,
    )

    rows: list[dict[str, Any]] = []
    for artist, recs in by_artist.items():
        if len(recs) < min_albums:
            continue
        years = [r["year"] for r in recs if r["year"] is not None]
        ratings = [r["rating"] for r in recs if r["rating"] is not None]
        genre_counter: Counter[str] = Counter()
        for r in recs:
            for g in r["genres"]:
                genre_counter[str(g)] += 1
        main_genres = [g for g, _ in genre_counter.most_common(3)]
        rows.append(
            {
                "artist": artist,
                "albums": len(recs),
                "first_year": min(years) if years else None,
                "last_year": max(years) if years else None,
                "avg_rating": sum(ratings) / len(ratings) if ratings else None,
                "main_genres": ", ".join(main_genres),
            },
        )

    rows.sort(key=lambda r: (-(r["albums"] or 0), r["artist"].lower()))
    st.dataframe(rows, use_container_width=True)


def render_authors_page(records: list[dict[str, Any]]) -> None:
    """Overview by author: review counts, ratings, and favorite genres."""
    st.subheader("Authors overview")

    by_author: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        author = rec.get("author")
        if not author:
            continue
        by_author.setdefault(str(author), []).append(rec)

    if not by_author:
        st.info("No authors found in the data.")
        return

    min_reviews = st.slider(
        "Minimum reviews per author",
        min_value=1,
        max_value=max(len(v) for v in by_author.values()),
        value=1,
    )

    rows: list[dict[str, Any]] = []
    for author, recs in by_author.items():
        if len(recs) < min_reviews:
            continue
        years = [r["year"] for r in recs if r["year"] is not None]
        ratings = [r["rating"] for r in recs if r["rating"] is not None]
        genre_counter: Counter[str] = Counter()
        for r in recs:
            for g in r["genres"]:
                genre_counter[str(g)] += 1
        main_genres = [g for g, _ in genre_counter.most_common(3)]
        rows.append(
            {
                "author": author,
                "reviews": len(recs),
                "first_year": min(years) if years else None,
                "last_year": max(years) if years else None,
                "avg_rating": sum(ratings) / len(ratings) if ratings else None,
                "favorite_genres": ", ".join(main_genres),
            },
        )

    rows.sort(key=lambda r: (-(r["reviews"] or 0), r["author"].lower()))
    st.dataframe(rows, use_container_width=True)


def render_years_page(records: list[dict[str, Any]]) -> None:
    """Overview by year: review counts, average rating, and top genres."""
    st.subheader("Years overview")

    by_year: dict[int, list[dict[str, Any]]] = {}
    for rec in records:
        year = rec["year"]
        if year is None:
            continue
        by_year.setdefault(year, []).append(rec)

    rows: list[dict[str, Any]] = []
    for year, recs in sorted(by_year.items()):
        ratings = [r["rating"] for r in recs if r["rating"] is not None]
        genre_counter: Counter[str] = Counter()
        for r in recs:
            for g in r["genres"]:
                genre_counter[str(g)] += 1
        top_genres = [g for g, _ in genre_counter.most_common(3)]
        rows.append(
            {
                "year": year,
                "albums": len(recs),
                "avg_rating": sum(ratings) / len(ratings) if ratings else None,
                "top_genres": ", ".join(top_genres),
            },
        )

    st.dataframe(rows, use_container_width=True)


def _recommendations_css() -> None:
    st.markdown(
        """
        <style>
        .rec-page-title {
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        .rec-page-desc { color: #6b7280; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .rec-card {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }
        .rec-card:hover { border-color: #d1d5db; }
        .rec-header { margin-bottom: 0.35rem; }
        .rec-title {
            font-size: 1.05rem;
            font-weight: 600;
            text-decoration: none;
            color: #111827;
        }
        .rec-title:hover { text-decoration: underline; color: #1d4ed8; }
        .rec-meta { font-size: 0.8rem; color: #6b7280; margin-bottom: 0.5rem; }
        .rec-excerpt { font-size: 0.85rem; line-height: 1.5; color: #4b5563; }
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


def _communities_css() -> None:
    """Lightweight styling for community 'chips'."""
    st.markdown(
        """
        <style>
        /* Make checkboxes look like rounded chips in the main area */
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label {
            background-color: #f3f4f6;
            border-radius: 999px;
            border: 1px solid #e5e7eb;
            padding: 0.15rem 0.6rem;
            margin: 0.15rem 0.2rem;
            display: inline-flex;
            align-items: center;
            justify-content: flex-start;
            font-size: 0.8rem;
            cursor: pointer;
            white-space: nowrap;
        }
        div[data-testid="stHorizontalBlock"]
        div[data-testid="stCheckbox"] > label:hover {
            border-color: #9ca3af;
            background-color: #eef2ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_recommendations_page(metadata_map: dict[int, dict]) -> None:
    """Semantic search over reviews using the Chroma index; show recommendations."""
    _recommendations_css()

    st.markdown('<p class="rec-page-title">Recommendations</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rec-page-desc">Describe what you\'re in the mood for. '
        "Results are similar reviews from the index.</p>",
        unsafe_allow_html=True,
    )

    col_query, col_filters = st.columns([2, 1])
    with col_query:
        query = st.text_area(
            "Search",
            placeholder="e.g. Grunge mit Melodien, ruhiger Jazz, laute Gitarren",
            label_visibility="collapsed",
            height=220,
        )
    with col_filters:
        n_results = st.slider(
            "Number of results",
            min_value=3,
            max_value=20,
            value=8,
        )
        year_range = st.slider(
            "Release year",
            min_value=1990,
            max_value=2030,
            value=(1990, 2030),
            step=1,
        )
        rating_range = st.slider(
            "Rating (0-10)",
            min_value=0,
            max_value=10,
            value=(0, 10),
            step=1,
        )
        all_genres: set[str] = set()
        for meta in metadata_map.values():
            if isinstance(meta, dict):
                for g in meta.get("genres") or []:
                    if isinstance(g, str) and g.strip():
                        all_genres.add(g.strip())
        selected_genres = st.multiselect(
            "Genres (OR)",
            options=sorted(all_genres),
            default=[],
            help="Select one or more genres. Results match any selected genre.",
        )

    min_year, max_year = year_range[0], year_range[1]
    min_rating, max_rating = int(rating_range[0]), int(rating_range[1])

    conditions: list[dict[str, Any]] = []
    if min_year > 1990:
        conditions.append({"release_year": {"$gte": int(min_year)}})
    if max_year < 2030:
        conditions.append({"release_year": {"$lte": int(max_year)}})
    if min_rating > 0:
        conditions.append({"rating": {"$gte": min_rating}})
    if max_rating < 10:
        conditions.append({"rating": {"$lte": max_rating}})
    # Genre filter is applied in Python from metadata_map.
    # This works without Chroma genre metadata.
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}
    else:
        where = None

    if not query or not query.strip():
        st.info("Enter a description above to get recommendations.")
        return

    # When filtering by genre we fetch more candidates, then filter in Python
    fetch_n = n_results * 5 if selected_genres else n_results
    try:
        hits = search_reviews(
            query.strip(),
            n_results=fetch_n,
            where=where,
        )
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            st.error(
                "OpenAI API key not set. "
                "Set OPENAI_API_KEY in your environment or .env."
            )
        else:
            st.error(f"Cannot search: {e}")
        return
    except Exception as e:
        st.error(f"Search failed: {e}")
        return

    if selected_genres:
        genre_set = set(selected_genres)
        filtered = []
        for h in hits:
            review_id = h.get("id")
            if not review_id:
                continue
            try:
                rid = int(review_id)
            except (ValueError, TypeError):
                continue
            doc_genres = metadata_map.get(rid, {}).get("genres") or []
            if not isinstance(doc_genres, list):
                doc_genres = []
            if genre_set.intersection(set(str(g) for g in doc_genres)):
                filtered.append(h)
            if len(filtered) >= n_results:
                break
        hits = filtered[:n_results]

    if not hits:
        st.warning(
            "No results found. Ensure the Chroma index is built "
            "(hatch run batch-embed run)."
        )
        return

    st.markdown(f"**{len(hits)} albums match your filters.**")

    cards: list[str] = []
    for i, hit in enumerate(hits, start=1):
        url = hit.get("url") or ""
        title = hit.get("title") or ""
        artist = hit.get("artist") or ""
        album = hit.get("album") or ""
        rating = hit.get("rating")
        year = hit.get("release_year")
        text = (hit.get("text") or "")[:400]
        if len(hit.get("text") or "") > 400:
            text += "\u2026"

        meta_parts: list[str] = []
        if rating is not None:
            meta_parts.append(f"{rating:.1f}/10")
        if year is not None:
            meta_parts.append(str(year))

        rank = f"{i:02d}"
        artist_esc = html.escape(artist)
        album_esc = html.escape(album)
        title_esc = html.escape(title) if title else ""
        if url:
            link_attrs = f'href="{html.escape(url)}" target="_blank" rel="noopener"'
            header_inner = (
                f'<a {link_attrs} class="rec-title">{artist_esc} - {album_esc}</a>'
            )
        else:
            header_inner = f'<span class="rec-title">{artist_esc} - {album_esc}</span>'
        if title_esc:
            header_inner += (
                f' <span style="color:#6b7280;font-weight:400;">. {title_esc}</span>'
            )

        meta_html = html.escape(" \u00b7 ".join(meta_parts)) if meta_parts else ""
        excerpt_html = html.escape(text).replace("\n", "<br>") if text else ""

        card = (
            f'<div class="rec-card">'
            f'<div class="rec-header"><span class="rec-rank">{rank}</span>'
            f"{header_inner}</div>"
        )
        if meta_html:
            card += f'<div class="rec-meta">{meta_html}</div>'
        if excerpt_html:
            card += f'<div class="rec-excerpt">{excerpt_html}</div>'
        card += "</div>"
        cards.append(card)

    num_cols = 3
    for row_start in range(0, len(cards), num_cols):
        row_cards = cards[row_start : row_start + num_cols]
        cols = st.columns(num_cols)
        for c, col in enumerate(cols):
            with col:
                if c < len(row_cards):
                    st.markdown(row_cards[c], unsafe_allow_html=True)


def render_communities_page() -> None:
    """Overview of fixed clusterings and album affinities."""

    _communities_css()

    @st.cache_data(ttl=3600)
    def _load_clusterings(base_dir: str) -> dict[float, list[dict[str, Any]]]:
        resolutions = [10.0]
        clusterings: dict[float, list[dict[str, Any]]] = {}
        for res in resolutions:
            res_name = (
                str(int(res)) if float(res).is_integer() else str(res).replace(".", "_")
            )
            path = Path(base_dir) / f"communities_res_{res_name}.json"
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            comms = data.get("communities")
            if isinstance(comms, list):
                clusterings[float(res)] = [
                    c for c in comms if isinstance(c, dict) and c.get("id")
                ]
        return clusterings

    data_dir = resolve_data_path("data")
    clusterings = _load_clusterings(str(data_dir))

    if not clusterings:
        st.warning(
            "No fixed clusterings found. Run\n\n"
            '`hatch run graph-build -- --export-communities "10"`\n\n'
            "to generate communities_res_10.json and community_memberships.jsonl."
        )
        return

    st.subheader("Fixed clusterings (resolution 10)")

    available_res = sorted(clusterings.keys())
    res_labels = {
        r: f"Resolution {int(r) if float(r).is_integer() else r}" for r in available_res
    }
    selected_res = st.sidebar.selectbox(
        "Select resolution",
        options=available_res,
        format_func=lambda r: res_labels[r],
        index=available_res.index(10.0) if 10.0 in available_res else 0,
    )

    communities = clusterings.get(selected_res, [])
    if not communities:
        st.info(f"No communities found for resolution {selected_res}.")
        return

    sizes = [int(c.get("size", 0)) for c in communities]
    st.markdown(
        f"**Resolution:** {selected_res} · "
        f"**Communities:** {len(communities)} · "
        f"**Avg size:** {sum(sizes) / len(sizes):.1f} · "
        f"**Min/Max size:** {min(sizes)} / {max(sizes)}"
    )

    rows: list[dict[str, Any]] = []
    for c in communities:
        rows.append(
            {
                "ID": c.get("id"),
                "Size": c.get("size"),
                "Centroid": c.get("centroid") or "",
                "Top artists": ", ".join(c.get("top_artists") or []),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- Album → community affinities ---
    @st.cache_data(ttl=3600)
    def _load_affinities(path: str) -> list[dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            return []
        records: list[dict[str, Any]] = []
        for obj in iter_jsonl_objects(p, log_errors=False):
            if isinstance(obj, dict) and "review_id" in obj and "communities" in obj:
                records.append(obj)
        return records

    affinities_path = resolve_data_path("data/album_community_affinities.jsonl")
    affinities = _load_affinities(str(affinities_path))

    @st.cache_data(ttl=3600)
    def _load_genre_labels(base_dir: str, res_name: str) -> list[dict[str, Any]]:
        path = Path(base_dir) / f"community_genre_labels_res_{res_name}.json"
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        labels = data.get("labels")
        return labels if isinstance(labels, list) else []

    st.subheader("Album → community affinities")
    if not affinities:
        st.info(
            "No album community affinities found. Run\n\n"
            '`hatch run graph-build -- --export-communities "10" '
            "--export-album-affinities`\n\n"
            "to generate data/album_community_affinities.jsonl."
        )
        return

    # Build lookup for centroid names per resolution and community ID
    centroid_labels: dict[str, dict[str, str]] = {}
    for res, comms in clusterings.items():
        res_key = f"res_{int(res)}" if float(res).is_integer() else f"res_{res}"
        centroid_labels[res_key] = {
            str(c.get("id")): str(c.get("centroid") or c.get("id"))
            for c in comms
            if c.get("id")
        }

    def _format_labels_for_res(
        row: dict[str, Any],
        res_key: str,
    ) -> str:
        comms = row.get("communities", {})
        if not isinstance(comms, dict):
            return ""
        entries = comms.get(res_key)
        if not isinstance(entries, list):
            return ""
        labels = centroid_labels.get(res_key, {})
        parts: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            cid = str(entry.get("id"))
            score = entry.get("score")
            if score is None:
                continue
            name = labels.get(cid, cid)
            parts.append(f"{name} ({score:.2f})")
        return ", ".join(parts)

    res10_key = "res_10"

    table_rows: list[dict[str, Any]] = []
    for obj in affinities:
        table_rows.append(
            {
                "Artist": obj.get("artist", ""),
                "Album": obj.get("album", ""),
                "Resolution 10": _format_labels_for_res(obj, res10_key),
            }
        )

    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    # --- Simple recommendations based on liked communities ---
    st.subheader("Pick communities you like")
    st.caption(
        "Choose a resolution and communities that feel like your taste. "
        "We will rank albums by how strongly they belong to these communities."
    )

    # Single active resolution (10) for preferences
    selected_res_key = res10_key
    if selected_res_key not in centroid_labels:
        return

    # Build options for clickable "chip" selection from communities
    # at selected resolution (ID: Centroid (size))
    inv_res_map: dict[str, float] = {}
    for res, _comms in clusterings.items():
        key = f"res_{int(res)}" if float(res).is_integer() else f"res_{res}"
        inv_res_map[key] = float(res)

    res_val = inv_res_map.get(selected_res_key)
    comms_for_res = clusterings.get(res_val, []) if res_val is not None else []

    st.markdown("**Click communities below to mark them as liked.**")
    num_cols = 4
    cols = st.columns(num_cols)
    liked_ids: set[str] = set()
    for idx, c in enumerate(comms_for_res):
        cid = str(c.get("id"))
        name = str(c.get("centroid") or cid)
        size = int(c.get("size", 0))
        col = cols[idx % num_cols]
        key = f"like_{selected_res_key}_{cid}"
        label = f"{cid}: {name} ({size})"
        with col:
            checked = st.checkbox(label, key=key)
        if checked:
            liked_ids.add(cid)

    # Optional per-community weights (default 1.0) for liked communities
    weights: dict[str, float] = {}
    if liked_ids:
        with st.expander("Adjust community weights", expanded=False):
            for cid in sorted(liked_ids):
                weight_key = f"weight_{selected_res_key}_{cid}"
                weights[cid] = st.slider(
                    f"{cid} weight",
                    min_value=0.1,
                    max_value=3.0,
                    value=1.0,
                    step=0.1,
                    key=weight_key,
                )

    res_name = selected_res_key.replace("res_", "")
    genre_labels_list = _load_genre_labels(str(data_dir), res_name)
    if genre_labels_list:
        genre_to_cid: dict[str, str] = {
            str(item.get("genre_label", "")): str(item.get("community_id", ""))
            for item in genre_labels_list
            if item.get("genre_label") and item.get("community_id")
        }
        genre_items = sorted(genre_to_cid.items())
        if genre_items:
            st.markdown("**Or click genres you like (adds those communities):**")
            genre_cols = st.columns(num_cols)
            for idx, (genre_label, cid) in enumerate(genre_items):
                col = genre_cols[idx % num_cols]
                key = f"like_genre_{selected_res_key}_{cid}_{idx}"
                with col:
                    checked = st.checkbox(genre_label, key=key)
                if checked:
                    liked_ids.add(cid)

    score_threshold = st.slider(
        "Minimum score (sum of affinities over liked communities)",
        min_value=0.0,
        max_value=1.0,
        value=0.30,
        step=0.05,
    )

    if liked_ids:
        # Additional filters on the scored list (rating, year, score, diversity, sort)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            min_rating = st.slider(
                "Min rating",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.5,
            )
        with col_f2:
            year_range = st.slider(
                "Release year",
                min_value=1990,
                max_value=2030,
                value=(1990, 2030),
                step=1,
            )
        with col_f3:
            score_min, score_max = st.slider(
                "Score range",
                min_value=0.0,
                max_value=1.0,
                value=(0.0, 1.0),
                step=0.05,
            )

        col_f4, col_f5 = st.columns(2)
        with col_f4:
            min_hits_pct = st.slider(
                "Min genre-hits (%)",
                min_value=0,
                max_value=100,
                value=0,
                step=5,
            )
        with col_f5:
            sort_mode = st.selectbox(
                "Sort order",
                options=["Deterministic", "Serendipity"],
                index=0,
            )
            serendipity = st.slider(
                "Serendipity",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.1,
                disabled=(sort_mode != "Serendipity"),
            )

        # Compute scores that favour albums connected to many liked communities.
        # For each album we track:
        # - k: number of liked communities it touches (score > 0)
        # - S: sum of (weight(c) * affinity) over liked communities
        raw_scored: list[dict[str, Any]] = []
        for obj in affinities:
            comms = obj.get("communities", {})
            if not isinstance(comms, dict):
                continue
            entries = comms.get(selected_res_key)
            if not isinstance(entries, list):
                continue
            s = 0.0  # sum of weighted scores over liked communities
            k_hits = 0  # how many liked communities get score > 0
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cid = str(entry.get("id"))
                if cid in liked_ids:
                    score_val = entry.get("score")
                    if isinstance(score_val, (int, float)):
                        val = float(score_val)
                        w = weights.get(cid, 1.0)
                        s += w * val
                        if val > 0:
                            k_hits += 1
            if k_hits > 0 and s >= score_threshold:
                raw_scored.append({"k_hits": k_hits, "score": s, "obj": obj})

        if raw_scored:
            # Lazy-load reviews to enrich with rating/year
            @st.cache_data(ttl=3600)
            def _load_review_index() -> dict[int, Any]:
                from music_review.io.reviews_jsonl import load_reviews_from_jsonl

                path = resolve_data_path("data/reviews.jsonl")
                if not path.exists():
                    return {}
                index: dict[int, Any] = {}
                reviews_local = load_reviews_from_jsonl(path)
                for r in reviews_local:
                    index[int(r.id)] = r
                return index

            review_index = _load_review_index()

            # Apply filters
            filtered_scored: list[dict[str, Any]] = []
            total_liked = len(liked_ids) if liked_ids else 1
            for item in raw_scored:
                obj = item["obj"]
                review_id = obj.get("review_id")
                review = (
                    review_index.get(int(review_id))
                    if isinstance(review_id, int)
                    else None
                )
                rating_val: float | None = None
                year_val: int | None = None
                if review is not None:
                    rating_val = review.rating
                    if review.release_year is not None:
                        year_val = review.release_year
                    elif review.release_date is not None:
                        year_val = review.release_date.year

                # Rating filter
                if rating_val is not None and rating_val < min_rating:
                    continue
                # Year filter
                if year_val is not None and not (
                    year_range[0] <= year_val <= year_range[1]
                ):
                    continue
                # Score range
                if not (score_min <= item["score"] <= score_max):
                    continue

                hits_pct = 100.0 * item["k_hits"] / total_liked
                if hits_pct < min_hits_pct:
                    continue

                item["rating"] = rating_val
                item["year"] = year_val
                item["hits_pct"] = hits_pct
                filtered_scored.append(item)

            # Sort
            if sort_mode == "Deterministic" or serendipity == 0.0:
                filtered_scored.sort(
                    key=lambda x: (x["k_hits"], x["score"]),
                    reverse=True,
                )
            else:
                import random

                rng = random.Random(42)
                for item in filtered_scored:
                    base = item["score"]
                    noise = rng.random()
                    item["serendipity_score"] = (1.0 - serendipity) * base + (
                        serendipity * noise
                    )
                filtered_scored.sort(
                    key=lambda x: x["serendipity_score"],
                    reverse=True,
                )

            if not filtered_scored:
                st.info("No albums match the current filters.")
                return

            st.markdown(f"**{len(filtered_scored)} albums match your filters.**")

            st.markdown("**Recommended albums (by community affinity):**")

            rec_rows: list[dict[str, Any]] = []
            allowed_review_ids: set[int] = set()
            for item in filtered_scored:
                obj = item["obj"]
                review_id_val = obj.get("review_id")
                if isinstance(review_id_val, int):
                    allowed_review_ids.add(review_id_val)
                score_val = item["score"]
                rating_val = item.get("rating")
                year_val = item.get("year")

                genre_hits_pct = item["hits_pct"]
                rec_rows.append(
                    {
                        "Artist": obj.get("artist", ""),
                        "Album": obj.get("album", ""),
                        "Score": f"{score_val:.2f}",
                        "Genre-Hits (%)": f"{genre_hits_pct:.0f}",
                        "Communities (res 10)": _format_labels_for_res(obj, res10_key),
                        "Rating": f"{rating_val:.1f}"
                        if isinstance(rating_val, (int, float))
                        else "",
                        "Release year": year_val if year_val is not None else "",
                        "Review": obj.get("url", ""),
                    }
                )
            st.dataframe(rec_rows, use_container_width=True, hide_index=True)

            # Optional free-text search (RAG) restricted to the filtered albums
            # Controls for free-text search (RAG) restricted to the filtered albums
            rag_query = st.text_area(
                "Describe what you're looking for (search within these albums)",
                key="communities_rag_query",
                height=140,
            )
            max_distance = st.slider(
                "Max semantic distance (lower = more similar)",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.05,
            )
            if rag_query and rag_query.strip() and allowed_review_ids:
                query_text = rag_query.strip()
                _debug_log(
                    run_id="pre-fix",
                    hypothesis_id="H1",
                    location="streamlit_app.py:communities_rag_before_search",
                    message="RAG search request",
                    data={
                        "query": query_text,
                        "allowed_review_ids_count": len(allowed_review_ids),
                        "liked_ids_count": len(liked_ids),
                        "max_distance": max_distance,
                    },
                )
                st.markdown(
                    f"**Free-text search within these albums:** `{query_text}`",
                )
                # We restrict in Python to the exact filtered album set; Chroma
                # search is run without an additional metadata where-clause to
                # avoid over-filtering when community metadata is missing.
                where: dict[str, Any] | None = None
                try:
                    hits = search_reviews(
                        query_text,
                        n_results=min(100, len(allowed_review_ids)),
                        where=where,
                    )
                except Exception as exc:
                    st.error(f"RAG search failed: {exc}")
                else:
                    filtered_hits: list[dict[str, Any]] = []
                    _debug_log(
                        run_id="pre-fix",
                        hypothesis_id="H2",
                        location="streamlit_app.py:communities_rag_after_search",
                        message="RAG raw hits",
                        data={
                            "raw_hits_count": len(hits),
                            "allowed_review_ids_count": len(allowed_review_ids),
                            "where": where,
                        },
                    )
                    for h in hits:
                        doc_id = h.get("id")
                        distance = h.get("distance")
                        try:
                            rid = int(doc_id)
                        except (TypeError, ValueError):
                            continue
                        if rid not in allowed_review_ids:
                            continue
                        if (
                            isinstance(distance, (int, float))
                            and float(
                                distance,
                            )
                            > max_distance
                        ):
                            continue
                        filtered_hits.append(h)
                        if len(filtered_hits) >= 10:
                            break

                    if filtered_hits:
                        _debug_log(
                            run_id="pre-fix",
                            hypothesis_id="H3",
                            location="streamlit_app.py:communities_rag_after_filter",
                            message="RAG filtered hits",
                            data={
                                "filtered_hits_count": len(filtered_hits),
                                "raw_hits_count": len(hits),
                                "allowed_review_ids_count": len(allowed_review_ids),
                                "max_distance": max_distance,
                            },
                        )
                        st.markdown(
                            f"**{len(filtered_hits)} RAG matches "
                            "(raw hits: "
                            f"{len(hits)}, filtered albums: "
                            f"{len(allowed_review_ids)}).**",
                        )
                        st.markdown("**Free-text matches within these albums:**")
                        for i, h in enumerate(filtered_hits, start=1):
                            artist = h.get("artist") or ""
                            album = h.get("album") or ""
                            rating = h.get("rating")
                            year = h.get("release_year")
                            url = h.get("url") or ""
                            text = (h.get("text") or "")[:300]
                            if len(h.get("text") or "") > 300:
                                text += "..."

                            header = f"{i}. {artist} — {album}"
                            if rating is not None or year is not None:
                                meta_parts: list[str] = []
                                if rating is not None:
                                    meta_parts.append(f"{rating:.1f}/10")
                                if year is not None:
                                    meta_parts.append(str(year))
                                header += " (" + ", ".join(meta_parts) + ")"
                            if url:
                                st.markdown(f"[{header}]({url})")
                            else:
                                st.markdown(header)
                            st.write(text)
                    else:
                        st.info(
                            f"No RAG matches within the filtered albums "
                            "(raw hits from index: "
                            f"{len(hits)}, filtered albums: "
                            f"{len(allowed_review_ids)}).",
                        )


def main() -> None:
    st.set_page_config(
        page_title="Music Review Dashboard",
        page_icon="🎵",
        layout="wide",
    )
    st.title("🎵 Music Review Dashboard")
    st.caption("Browse plattentests.de reviews and MusicBrainz metadata.")

    reviews, metadata_map = load_data()
    if not reviews:
        st.warning(
            "No reviews found. Run the pipeline first: "
            "`hatch run update-db` or scrape into `data/reviews.jsonl`.",
        )
        return

    records = build_records(reviews, metadata_map)

    page = st.sidebar.radio(
        "View",
        options=[
            "Recommendations",
            "Browse",
            "Communities",
            "Genres",
            "Artists",
            "Authors",
            "Years",
        ],
        index=1,
    )

    if page == "Recommendations":
        render_recommendations_page(metadata_map)
    elif page == "Browse":
        render_browse_page(reviews, metadata_map)
    elif page == "Communities":
        render_communities_page()
    elif page == "Genres":
        render_genres_page(records)
    elif page == "Artists":
        render_artists_page(records)
    elif page == "Authors":
        render_authors_page(records)
    elif page == "Years":
        render_years_page(records)


if __name__ == "__main__":
    main()
