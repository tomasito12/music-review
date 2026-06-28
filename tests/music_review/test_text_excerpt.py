"""Tests for review excerpt preview building."""

from __future__ import annotations

from music_review.text_excerpt import build_text_excerpt


def test_build_text_excerpt_returns_short_text_unchanged() -> None:
    """Short reviews are returned whole and not marked as truncated."""
    text = "Kurzer Rezensionstext."
    excerpt, continues = build_text_excerpt(text, limit=300)
    assert excerpt == text
    assert continues is False


def test_build_text_excerpt_truncates_on_word_boundary() -> None:
    """Long reviews are cut at the last space before the limit."""
    text = "Alpha " + ("beta " * 80)
    excerpt, continues = build_text_excerpt(text, limit=40)
    assert continues is True
    assert len(excerpt) <= 40
    assert not excerpt.endswith("be")
    assert excerpt.endswith("beta")


def test_build_text_excerpt_repairs_encoding_before_truncating() -> None:
    """Broken punctuation is repaired before the excerpt is built."""
    text = ("Wort " * 70) + "ausgeschieden \x96 blo\u00df"
    excerpt, continues = build_text_excerpt(text, limit=50)
    assert continues is True
    assert "\x96" not in excerpt
    assert "\u2013" in excerpt or excerpt.endswith("Wort")
