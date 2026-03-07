#!/usr/bin/env python3
"""Streamlit dashboard to browse music reviews and metadata."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path
from music_review.io.jsonl import load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl


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
        if selected_genres:
            if not any(g in selected_genres for g in rec["genres"]):
                return False
        if year_range and rec["year"] is not None:
            if not (year_range[0] <= rec["year"] <= year_range[1]):
                return False
        if min_rating is not None and rec["rating"] is not None:
            if rec["rating"] < min_rating:
                return False
        return True

    filtered = [rec for rec in records if _matches_filters(rec)]

    genre_counts: Counter[str] = Counter()
    for rec in filtered:
        for g in rec["genres"]:
            genre_counts[str(g)] += 1

    genre_rows = [
        {"genre": genre, "albums": count}
        for genre, count in genre_counts.most_common()
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
        options=["Browse", "Genres", "Artists", "Authors", "Years"],
        index=0,
    )

    if page == "Browse":
        render_browse_page(reviews, metadata_map)
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
