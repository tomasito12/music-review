"""Focused unit tests for vector_store pure logic."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.domain.models import Review
from music_review.pipeline.retrieval import vector_store


def test_hybrid_chunk_text_merges_short_paragraphs() -> None:
    """Short paragraphs are merged into fewer chunks."""
    text = "A" * 120 + "\n\n" + "B" * 120 + "\n\n" + "C" * 120
    chunks = vector_store.hybrid_chunk_text(
        text,
        min_chunk_chars=50,
        target_chunk_chars=240,
        max_chunk_chars=400,
    )
    assert len(chunks) <= 2
    assert "A" * 20 in chunks[0]


def test_hybrid_chunk_text_splits_long_text() -> None:
    """Very long text is split into bounded chunk lengths."""
    long_sentence = "x" * 1200
    text = long_sentence + "\n\n" + long_sentence
    chunks = vector_store.hybrid_chunk_text(
        text,
        min_chunk_chars=200,
        target_chunk_chars=500,
        max_chunk_chars=600,
    )
    assert len(chunks) >= 3
    assert all(len(c) <= 600 for c in chunks)


def test_generate_query_variants_strategy_a_returns_original() -> None:
    """Strategy A returns exactly the original query."""
    query = "spröde monoton"
    assert vector_store.generate_query_variants(query, strategy="A") == [query]


def test_generate_query_variants_strategy_b_expands_and_unique() -> None:
    """Strategy B returns original plus stable unique expansions."""
    variants = vector_store.generate_query_variants(
        "spröde monoton",
        strategy="B",
        max_variants=5,
    )
    assert variants
    assert variants[0] == "spröde monoton"
    assert len(variants) <= 5
    assert len(variants) == len(set(variants))


def test_generate_query_variants_strategy_c_adds_intent_variant() -> None:
    """Strategy C includes an additional intent-like variant."""
    variants_b = vector_store.generate_query_variants(
        "melancholisch gitarren",
        strategy="B",
        max_variants=6,
    )
    variants_c = vector_store.generate_query_variants(
        "melancholisch gitarren",
        strategy="C",
        max_variants=6,
    )
    assert len(variants_c) >= len(variants_b)
    assert any(v != "melancholisch gitarren" for v in variants_c)


def test_parse_batch_output_lines_skips_error_rows(tmp_path: Path) -> None:
    """Only successful embedding rows are returned."""
    path = tmp_path / "batch_output.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "custom_id": "1",
                        "response": {"body": {"data": [{"embedding": [0.1, 0.2]}]}},
                    }
                ),
                json.dumps({"custom_id": "2", "error": {"message": "bad"}}),
                "not-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    parsed = vector_store._parse_batch_output_lines(path)
    assert parsed == [("1", [0.1, 0.2])]


def test_review_to_metadata_and_enriched_document() -> None:
    """Metadata and enriched text contain core review properties."""
    review = Review(
        id=11,
        url="https://example.com/review/11",
        artist="Band",
        album="Album",
        text="Body text",
        title="Title",
        author="Author",
        labels=["Label"],
        release_year=2024,
        rating=8.0,
        highlights=["Track A"],
        references=["Other Band"],
    )
    meta = vector_store.review_to_metadata(review)
    assert meta["artist"] == "Band"
    assert meta["release_year"] == 2024
    assert meta["review_text"] == "Body text"

    enriched = vector_store.build_enriched_document(
        review,
        {"genres": ["indie_rock"]},
    )
    assert "Artist: Band." in enriched
    assert "Genres: indie_rock." in enriched
    assert enriched.endswith("Body text")


def test_chunk_to_metadata_includes_chunk_fields() -> None:
    """Chunk metadata keeps review join keys and chunk payload."""
    review = Review(
        id=5,
        url="https://example.com/review/5",
        artist="Artist",
        album="Album",
        text="Review",
    )
    meta = vector_store.chunk_to_metadata(
        review,
        chunk_index=2,
        chunk_text="snippet",
    )
    assert meta["review_id"] == 5
    assert meta["chunk_index"] == 2
    assert meta["chunk_text"] == "snippet"


def test_search_reviews_with_variants_deduplicates_by_best_distance(
    monkeypatch,
) -> None:
    """Variant search keeps one hit per review_id with best distance."""

    def fake_search_reviews(
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, object] | None = None,
        collection_name: str | None = None,
    ) -> list[dict[str, object]]:
        if "karg" in query_text:
            return [
                {"review_id": 1, "distance": 0.30, "artist": "A", "album": "B"},
                {"review_id": 2, "distance": 0.40, "artist": "C", "album": "D"},
            ]
        return [
            {"review_id": 1, "distance": 0.20, "artist": "A", "album": "B"},
            {"review_id": 3, "distance": 0.50, "artist": "E", "album": "F"},
        ]

    monkeypatch.setattr(vector_store, "search_reviews", fake_search_reviews)

    hits = vector_store.search_reviews_with_variants(
        "spröde",
        strategy="B",
        n_results=5,
        top_k_per_variant=5,
    )
    ids = [h.get("review_id") for h in hits]
    assert ids.count(1) == 1
    best_for_one = next(h for h in hits if h.get("review_id") == 1)
    assert best_for_one.get("distance") == 0.20


def test_search_reviews_with_variants_strategy_c_applies_rank_bonus(
    monkeypatch,
) -> None:
    """Strategy C can promote consistently matching review IDs."""

    def fake_variants(
        query_text: str,
        *,
        strategy: str = "B",
        max_variants: int = 4,
    ) -> list[str]:
        return ["v1", "v2"]

    def fake_search_reviews(
        query_text: str,
        *,
        n_results: int = 5,
        where: dict[str, object] | None = None,
        collection_name: str | None = None,
    ) -> list[dict[str, object]]:
        if query_text == "v1":
            return [{"review_id": 1, "distance": 0.40}]
        if query_text == "v2":
            return [
                {"review_id": 1, "distance": 0.39},
                {"review_id": 2, "distance": 0.38},
            ]
        return []

    monkeypatch.setattr(vector_store, "generate_query_variants", fake_variants)
    monkeypatch.setattr(vector_store, "search_reviews", fake_search_reviews)

    hits = vector_store.search_reviews_with_variants(
        "query",
        strategy="C",
        n_results=5,
        top_k_per_variant=5,
    )
    # review_id=1 appears in two variants and should rank first.
    assert hits
    assert hits[0].get("review_id") == 1
