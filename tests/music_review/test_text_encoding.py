"""Tests for plattentests.de text encoding repair."""

from __future__ import annotations

from music_review.text_encoding import repair_plattentests_text


def test_repair_plattentests_text_replaces_en_dash() -> None:
    """C1 control U+0096 becomes an en dash."""
    broken = "ausgeschieden \x96 blo\u00df zwei Jahre"
    expected = "ausgeschieden \u2013 blo\u00df zwei Jahre"
    assert repair_plattentests_text(broken) == expected


def test_repair_plattentests_text_replaces_em_dash_and_quotes() -> None:
    """Other common CP1252 punctuation is repaired too."""
    broken = "\x97 \x93Lighthouse\x94"
    assert repair_plattentests_text(broken) == "\u2014 \u201cLighthouse\u201d"


def test_repair_plattentests_text_leaves_clean_utf8_unchanged() -> None:
    """Already-correct German text and punctuation stay untouched."""
    clean = "Sch\u00f6n \u2013 bereits korrekt."
    assert repair_plattentests_text(clean) == clean


def test_repair_plattentests_text_handles_empty_string() -> None:
    """Empty input is returned unchanged."""
    assert repair_plattentests_text("") == ""
