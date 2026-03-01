#!/usr/bin/env python3
"""Streamlit dashboard to browse music reviews and metadata."""

from __future__ import annotations

import random

import streamlit as st

import music_review.config  # noqa: F401 - load .env and set up paths
from music_review.config import resolve_data_path
from music_review.io.jsonl import load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl


def load_data() -> tuple[list, dict[int, dict]]:
    """Load reviews and metadata; return (reviews_list, metadata_by_review_id)."""
    reviews_path = resolve_data_path("data/reviews.jsonl")
    metadata_path = resolve_data_path("data/metadata.jsonl")

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
            "`hatch run update-db` or scrape into `data/reviews.jsonl`."
        )
        return

    # Persist selection across reruns so "Select a random review" can set it
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
    other_parts = []
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


if __name__ == "__main__":
    main()
