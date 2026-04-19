"""Tests for the pure text chunking module."""

from __future__ import annotations

from music_review.pipeline.retrieval.chunking import (
    _hard_split_by_chars,
    _split_paragraph_into_sentences,
    _split_text_into_paragraphs,
    hybrid_chunk_text,
)


def test_split_text_into_paragraphs_basic() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird."
    result = _split_text_into_paragraphs(text)
    assert result == ["First paragraph.", "Second paragraph.", "Third."]


def test_split_text_into_paragraphs_strips_whitespace() -> None:
    text = "  A  \n\n  B  \n\n"
    result = _split_text_into_paragraphs(text)
    assert result == ["A", "B"]


def test_split_text_into_paragraphs_empty_string() -> None:
    assert _split_text_into_paragraphs("") == []


def test_split_paragraph_into_sentences_basic() -> None:
    para = "Hello world. How are you? I'm fine!"
    result = _split_paragraph_into_sentences(para)
    assert result == ["Hello world.", "How are you?", "I'm fine!"]


def test_split_paragraph_into_sentences_normalizes_newlines() -> None:
    para = "First line.\nSecond line."
    result = _split_paragraph_into_sentences(para)
    assert result == ["First line.", "Second line."]


def test_split_paragraph_into_sentences_empty() -> None:
    assert _split_paragraph_into_sentences("") == []


def test_hard_split_by_chars_short_text() -> None:
    result = _hard_split_by_chars("abcde", max_chunk_chars=10)
    assert result == ["abcde"]


def test_hard_split_by_chars_long_text() -> None:
    result = _hard_split_by_chars("abcdefghij", max_chunk_chars=3)
    assert result == ["abc", "def", "ghi", "j"]


def test_hard_split_by_chars_empty() -> None:
    assert _hard_split_by_chars("", max_chunk_chars=5) == []
    assert _hard_split_by_chars("   ", max_chunk_chars=5) == []


def test_hybrid_chunk_text_empty_input() -> None:
    assert hybrid_chunk_text("") == []
    assert hybrid_chunk_text("   ") == []
    assert hybrid_chunk_text(None) == []  # type: ignore[arg-type]


def test_hybrid_chunk_text_single_short_paragraph() -> None:
    text = "This is a short review."
    result = hybrid_chunk_text(text, min_chunk_chars=5, max_chunk_chars=200)
    assert len(result) == 1
    assert result[0] == text


def test_hybrid_chunk_text_merges_short_paragraphs() -> None:
    text = "A" * 120 + "\n\n" + "B" * 120 + "\n\n" + "C" * 120
    chunks = hybrid_chunk_text(
        text,
        min_chunk_chars=50,
        target_chunk_chars=240,
        max_chunk_chars=400,
    )
    assert len(chunks) <= 2
    assert "A" * 20 in chunks[0]


def test_hybrid_chunk_text_splits_long_paragraphs() -> None:
    long_sentence = "x" * 1200
    text = long_sentence + "\n\n" + long_sentence
    chunks = hybrid_chunk_text(
        text,
        min_chunk_chars=200,
        target_chunk_chars=500,
        max_chunk_chars=600,
    )
    assert len(chunks) >= 3
    assert all(len(c) <= 600 for c in chunks)


def test_hybrid_chunk_text_respects_max_chunk_chars() -> None:
    text = ("word " * 500).strip()
    chunks = hybrid_chunk_text(
        text,
        min_chunk_chars=100,
        target_chunk_chars=400,
        max_chunk_chars=500,
    )
    assert all(len(c) <= 500 for c in chunks)
    assert len(chunks) >= 2


def test_hybrid_chunk_text_merges_tiny_tail() -> None:
    p1 = "A" * 300
    p2 = "B" * 50
    text = p1 + "\n\n" + p2
    chunks = hybrid_chunk_text(
        text,
        min_chunk_chars=100,
        target_chunk_chars=200,
        max_chunk_chars=500,
    )
    assert len(chunks) == 1
    assert "A" in chunks[0] and "B" in chunks[0]
