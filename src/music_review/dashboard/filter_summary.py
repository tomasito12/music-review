"""Short German summaries of active taste filter settings."""

from __future__ import annotations

from music_review.application.models import TasteProfile


def format_profile_filter_summary(profile: TasteProfile) -> str:
    """Return a one-line summary of hard filters on the active profile."""
    settings = profile.filter_settings
    year_lo = settings.year_min if settings.year_min is not None else "Archiv-Min"
    year_hi = settings.year_max if settings.year_max is not None else "Archiv-Max"
    labels = settings.plattenlabel_selection
    label_text = "alle" if labels is None else f"{len(labels)} ausgewählt"
    return (
        f"Stilpassung: {settings.score_min:.2f}-{settings.score_max:.2f}, "
        f"Rating: {settings.rating_min:.0f}-{settings.rating_max:.0f}, "
        f"Jahr: {year_lo}-{year_hi}, Plattenlabel: {label_text}"
    )
