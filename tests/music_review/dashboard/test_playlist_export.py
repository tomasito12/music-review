"""Tests for TuneMyMusic playlist export formatting."""

from __future__ import annotations

from music_review.dashboard.playlist_builder import PlaylistSuggestion
from music_review.dashboard.playlist_export import (
    format_free_text,
    format_tune_my_music_csv,
    format_tune_my_music_txt,
    suggested_export_filename,
)


def _suggestion(
    *,
    review_id: int,
    artist: str,
    track_title: str,
) -> PlaylistSuggestion:
    return PlaylistSuggestion(
        review_id=review_id,
        artist=artist,
        album="Album",
        track_title=track_title,
        source_kind="highlight",
        score_weight=1.0,
        raw_score=1.0,
        playlist_slot_quota=1,
        strat_ideal_slots=1.0,
        strat_floor_slots=1,
        strat_remainder_extra_slots=0,
    )


def test_format_tune_my_music_txt_uses_artist_dash_title() -> None:
    """Each line follows the Artist - Title pattern."""
    text = format_tune_my_music_txt(
        [
            _suggestion(
                review_id=1,
                artist="Fontaines D.C.",
                track_title="Starburster",
            ),
            _suggestion(review_id=2, artist="Dry Cleaning", track_title="Leafy"),
        ],
    )
    assert text == "Fontaines D.C. - Starburster\nDry Cleaning - Leafy"


def test_format_tune_my_music_txt_preserves_order() -> None:
    """Export order matches the suggestion list order."""
    text = format_tune_my_music_txt(
        [
            _suggestion(review_id=1, artist="B", track_title="Two"),
            _suggestion(review_id=2, artist="A", track_title="One"),
        ],
    )
    assert text.splitlines() == ["B - Two", "A - One"]


def test_format_tune_my_music_txt_skips_blank_and_duplicates() -> None:
    """Empty artist/title rows and duplicate tracks are omitted."""
    text = format_tune_my_music_txt(
        [
            _suggestion(review_id=1, artist="A", track_title="Song"),
            _suggestion(review_id=2, artist="  ", track_title="Skip"),
            _suggestion(review_id=3, artist="A", track_title="Song"),
            _suggestion(review_id=4, artist="B", track_title="  "),
        ],
    )
    assert text == "A - Song"


def test_format_free_text_matches_txt() -> None:
    """Free-text export is identical to TXT export."""
    suggestions = [_suggestion(review_id=1, artist="X", track_title="Y")]
    assert format_free_text(suggestions) == format_tune_my_music_txt(suggestions)


def test_format_tune_my_music_csv_includes_header_and_playlist_name() -> None:
    """CSV uses TuneMyMusic column headers and the playlist name column."""
    csv_text = format_tune_my_music_csv(
        [_suggestion(review_id=1, artist="Fontaines D.C.", track_title="Starburster")],
        "Plattenradar 2026-06-20",
    )
    assert csv_text.splitlines() == [
        "Track name,Artist name,Playlist name",
        "Starburster,Fontaines D.C.,Plattenradar 2026-06-20",
    ]


def test_format_tune_my_music_csv_escapes_commas_in_fields() -> None:
    """CSV quoting handles commas inside track or artist names."""
    csv_text = format_tune_my_music_csv(
        [_suggestion(review_id=1, artist="A, B", track_title="Song, Part 1")],
        "My Playlist",
    )
    assert csv_text.splitlines()[1] == '"Song, Part 1","A, B",My Playlist'


def test_suggested_export_filename_sanitizes_special_characters() -> None:
    """Unsafe filename characters become hyphens or are removed."""
    assert (
        suggested_export_filename("Plattenradar: Test/2026")
        == "Plattenradar-Test2026.txt"
    )


def test_suggested_export_filename_supports_csv_extension() -> None:
    """CSV downloads use the .csv extension when requested."""
    assert (
        suggested_export_filename("Plattenradar 2026-06-20", extension=".csv")
        == "Plattenradar-2026-06-20.csv"
    )


def test_suggested_export_filename_fallback_when_empty() -> None:
    """Blank names fall back to a generic plattenradar filename."""
    assert suggested_export_filename("   ") == "plattenradar.txt"
