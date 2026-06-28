"""Build API-facing review excerpts with clean word boundaries."""

from __future__ import annotations

from music_review.text_encoding import repair_plattentests_text

DEFAULT_TEXT_EXCERPT_LIMIT = 300


def build_text_excerpt(
    text: str,
    *,
    limit: int = DEFAULT_TEXT_EXCERPT_LIMIT,
) -> tuple[str, bool]:
    """Return a preview snippet and whether the full review continues beyond it."""
    repaired = repair_plattentests_text(text).strip()
    if not repaired:
        return "", False
    if len(repaired) <= limit:
        return repaired, False

    snippet = repaired[:limit]
    last_space = snippet.rfind(" ")
    if last_space > limit // 2:
        snippet = snippet[:last_space]
    return snippet.rstrip(), True
