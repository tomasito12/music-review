"""Tests for compact German filter summaries."""

from __future__ import annotations

from music_review.application.models import TasteFilterSettings, TasteProfile
from music_review.dashboard.filter_summary import format_profile_filter_summary


def test_format_profile_filter_summary_uses_defaults_for_open_filters() -> None:
    profile = TasteProfile(
        selected_communities=("C001",),
        filter_settings=TasteFilterSettings(),
    )
    summary = format_profile_filter_summary(profile)
    assert "Stilpassung: 0.00-1.00" in summary
    assert "Rating: 6-10" in summary
    assert "Jahr: Archiv-Min-Archiv-Max" in summary
    assert "Plattenlabel: alle" in summary


def test_format_profile_filter_summary_shows_selected_labels() -> None:
    profile = TasteProfile(
        selected_communities=("C001",),
        filter_settings=TasteFilterSettings(
            year_min=1990,
            year_max=2010,
            score_min=0.4,
            rating_min=8,
            plattenlabel_selection=("Sub Pop", "Matador"),
        ),
    )
    summary = format_profile_filter_summary(profile)
    assert "1990-2010" in summary
    assert "Rating: 8-10" in summary
    assert "Plattenlabel: 2 ausgewählt" in summary
