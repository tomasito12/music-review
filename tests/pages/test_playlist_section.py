"""Tests for playlist suggestion UI helpers."""

from __future__ import annotations

from pages.playlist_section import _suggestions_to_display_rows

from music_review.dashboard.playlist_builder import PlaylistSuggestion


def test_suggestions_to_display_rows_maps_german_columns() -> None:
    """Display rows use German column labels and source-kind captions."""
    rows = _suggestions_to_display_rows(
        [
            PlaylistSuggestion(
                review_id=1,
                artist="Artist A",
                album="Album B",
                track_title="Song",
                source_kind="highlight",
                score_weight=0.5,
                raw_score=1.0,
                playlist_slot_quota=1,
                strat_ideal_slots=1.0,
                strat_floor_slots=1,
                strat_remainder_extra_slots=0,
            ),
        ],
    )
    assert rows == [
        {
            "Künstler": "Artist A",
            "Album": "Album B",
            "Titel": "Song",
            "Quelle": "Highlight",
        },
    ]
