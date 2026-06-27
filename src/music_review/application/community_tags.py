"""Helpers for recommendation-card community style tags."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

COMMUNITY_TAG_MIN_AFFINITY = 0.1


def community_tags_from_entries(
    entries: Sequence[Mapping[str, object]],
    *,
    label_for_id: Callable[[str], str],
    selected_community_ids: set[str] | frozenset[str] | None = None,
) -> list[dict[str, object]]:
    """Return card tags with affinity at or above the display threshold."""
    selected = (
        {community_id.strip().casefold() for community_id in selected_community_ids}
        if selected_community_ids
        else set()
    )
    ranked = sorted(
        (entry for entry in entries if isinstance(entry, Mapping)),
        key=lambda entry: float(str(entry.get("score", 0.0) or 0.0)),
        reverse=True,
    )
    tags: list[dict[str, object]] = []
    for entry in ranked:
        community_id = str(entry.get("id", "")).strip()
        affinity = float(str(entry.get("score", 0.0) or 0.0))
        if affinity < COMMUNITY_TAG_MIN_AFFINITY or not community_id:
            continue
        tags.append(
            {
                "id": community_id,
                "label": label_for_id(community_id),
                "affinity": affinity,
                "matched": community_id.casefold() in selected,
            },
        )
    return tags
