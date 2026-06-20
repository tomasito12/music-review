"""Export playlist suggestions for TuneMyMusic (TXT/CSV, no streaming APIs)."""

from __future__ import annotations

import csv
import io
import re
from typing import Literal

from music_review.dashboard.playlist_builder import (
    PlaylistSuggestion,
    catalog_lookup_key,
)

ExportExtension = Literal[".txt", ".csv"]

_FILENAME_UNSAFE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE_RE = re.compile(r"\s+")


def _export_lines(suggestions: list[PlaylistSuggestion]) -> list[tuple[str, str]]:
    """Return unique (artist, track_title) pairs in suggestion order."""
    seen: set[str] = set()
    lines: list[tuple[str, str]] = []
    for item in suggestions:
        artist = item.artist.strip()
        title = item.track_title.strip()
        if not artist or not title:
            continue
        key = catalog_lookup_key(artist, title)
        if key in seen:
            continue
        seen.add(key)
        lines.append((artist, title))
    return lines


def format_tune_my_music_txt(suggestions: list[PlaylistSuggestion]) -> str:
    """Format suggestions as TuneMyMusic free-text / TXT lines (Artist - Title)."""
    rows = _export_lines(suggestions)
    return "\n".join(f"{artist} - {title}" for artist, title in rows)


def format_free_text(suggestions: list[PlaylistSuggestion]) -> str:
    """Alias for :func:`format_tune_my_music_txt` (TuneMyMusic paste field)."""
    return format_tune_my_music_txt(suggestions)


def format_tune_my_music_csv(
    suggestions: list[PlaylistSuggestion],
    playlist_name: str,
) -> str:
    """Format suggestions as TuneMyMusic CSV (Track, Artist, Playlist name)."""
    name = playlist_name.strip() or "Plattenradar"
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["Track name", "Artist name", "Playlist name"])
    for artist, title in _export_lines(suggestions):
        writer.writerow([title, artist, name])
    return buffer.getvalue()


def suggested_export_filename(
    playlist_name: str,
    *,
    extension: ExportExtension = ".txt",
) -> str:
    """Build a safe local filename for a playlist export download."""
    base = playlist_name.strip() or "plattenradar"
    base = _FILENAME_UNSAFE_RE.sub("", base)
    base = _WHITESPACE_RE.sub("-", base).strip("-._")
    if not base:
        base = "plattenradar"
    return f"{base}{extension}"
