"""Tests for shared genre profile helpers."""

from __future__ import annotations

from collections import Counter

from music_review.pipeline.enrichment.genre_profiles import main_genres_from_counts


def test_main_genres_from_counts_empty() -> None:
    assert main_genres_from_counts({}, min_genre_share=0.15, top_k_main_genres=3) == []


def test_main_genres_from_counts_by_share() -> None:
    counts = Counter({"rock": 8, "pop": 2})
    assert main_genres_from_counts(
        counts,
        min_genre_share=0.5,
        top_k_main_genres=3,
    ) == ["rock"]


def test_main_genres_from_counts_top_k_fallback() -> None:
    counts = Counter({"a": 1, "b": 1, "c": 1})
    assert main_genres_from_counts(
        counts,
        min_genre_share=0.9,
        top_k_main_genres=2,
    ) == ["a", "b"]
