"""Shared genre profile aggregation helpers for enrichment pipelines."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping


def main_genres_from_counts(
    genre_counts: Mapping[str, int] | Counter[str],
    *,
    min_genre_share: float,
    top_k_main_genres: int,
) -> list[str]:
    """Derive main genres from aggregated counts using share and top-k fallback."""
    if not genre_counts:
        return []
    total = sum(genre_counts.values())
    main: list[str] = []
    counter = (
        genre_counts if isinstance(genre_counts, Counter) else Counter(genre_counts)
    )
    for genre, count in counter.most_common():
        if total > 0 and count / total >= min_genre_share:
            main.append(genre)
    if not main:
        for genre, _ in counter.most_common(top_k_main_genres):
            main.append(genre)
    return main
