"""Tests for the search module (pure logic, no Chroma/OpenAI required)."""

from __future__ import annotations

import math

import pytest

from music_review.pipeline.retrieval.search import (
    _extract_review_id,
    _l2_distance_vec,
    _normalize_query_text,
    generate_query_variants,
)


class TestNormalizeQueryText:
    def test_strips_and_lowercases(self) -> None:
        assert _normalize_query_text("  Hello World  ") == "hello world"

    def test_collapses_whitespace(self) -> None:
        assert _normalize_query_text("a   b\t c") == "a b c"

    def test_empty_string(self) -> None:
        assert _normalize_query_text("") == ""

    def test_preserves_umlauts(self) -> None:
        assert _normalize_query_text("Ärger Über Öde") == "ärger über öde"


class TestGenerateQueryVariants:
    def test_strategy_a_returns_original_only(self) -> None:
        assert generate_query_variants("hello", strategy="A") == ["hello"]

    def test_empty_query_returns_empty(self) -> None:
        assert generate_query_variants("") == []
        assert generate_query_variants("   ") == []

    def test_strategy_b_without_synonyms_adds_generic_suffixes(self) -> None:
        variants = generate_query_variants("xyzzy", strategy="B", max_variants=5)
        assert variants[0] == "xyzzy"
        assert len(variants) > 1
        assert any("music mood" in v for v in variants)

    def test_strategy_b_with_synonyms_expands(self) -> None:
        variants = generate_query_variants("spröde", strategy="B", max_variants=5)
        assert variants[0] == "spröde"
        assert any("karg" in v or "trocken" in v for v in variants)

    def test_strategy_c_includes_intent_variant(self) -> None:
        variants = generate_query_variants("monoton", strategy="C", max_variants=10)
        assert any("find review passage about:" in v for v in variants)

    def test_max_variants_respected(self) -> None:
        variants = generate_query_variants(
            "spröde monoton", strategy="B", max_variants=2
        )
        assert len(variants) <= 2

    def test_all_variants_unique(self) -> None:
        variants = generate_query_variants(
            "spröde monoton", strategy="B", max_variants=10
        )
        assert len(variants) == len(set(variants))


class TestExtractReviewId:
    def test_from_meta_int(self) -> None:
        assert _extract_review_id({"review_id": 42}, "ignored") == 42

    def test_from_meta_str(self) -> None:
        assert _extract_review_id({"review_id": "99"}, "ignored") == 99

    def test_from_doc_id_fallback(self) -> None:
        assert _extract_review_id({}, "123") == 123

    def test_none_on_invalid(self) -> None:
        assert _extract_review_id({}, "not-a-number") is None

    def test_none_on_non_numeric_meta(self) -> None:
        assert _extract_review_id({"review_id": "abc"}, "xyz") is None


class TestL2DistanceVec:
    def test_identical_vectors(self) -> None:
        assert _l2_distance_vec([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_distance(self) -> None:
        d = _l2_distance_vec([0.0, 0.0], [3.0, 4.0])
        assert d == pytest.approx(5.0)

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="dimension mismatch"):
            _l2_distance_vec([1.0], [1.0, 2.0])

    def test_single_dimension(self) -> None:
        assert _l2_distance_vec([5.0], [8.0]) == pytest.approx(3.0)

    def test_negative_values(self) -> None:
        d = _l2_distance_vec([-1.0, -2.0], [1.0, 2.0])
        expected = math.sqrt(4 + 16)
        assert d == pytest.approx(expected)
