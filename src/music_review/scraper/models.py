# src/music_review/scraper/models.py

"""Re-export domain models for backward compatibility."""

from music_review.domain.models import Review, Track

__all__ = ["Review", "Track"]
