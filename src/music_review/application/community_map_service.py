"""Cached access to the taste-community map layout."""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from typing import Any

from music_review.application.community_map_layout import (
    CommunityMapNode,
    build_community_map_layout,
    community_map_source_mtimes,
)

_MAP_LOCK = threading.RLock()
_MAP_CACHE: tuple[tuple[float, ...], tuple[CommunityMapNode, ...]] | None = None


def reset_community_map_cache() -> None:
    """Clear the module-level community map cache (for tests)."""
    global _MAP_CACHE
    with _MAP_LOCK:
        _MAP_CACHE = None


def get_community_map_layout(
    *,
    communities: Sequence[Mapping[str, Any]],
    memberships: dict[str, dict[str, str]],
) -> tuple[CommunityMapNode, ...]:
    """Return cached map nodes, rebuilding when source files change."""
    global _MAP_CACHE
    current_mtimes = community_map_source_mtimes()
    with _MAP_LOCK:
        if _MAP_CACHE is not None and _MAP_CACHE[0] == current_mtimes:
            return _MAP_CACHE[1]
        nodes = build_community_map_layout(
            communities=[dict(item) for item in communities],
            memberships=memberships,
        )
        _MAP_CACHE = (current_mtimes, nodes)
        return nodes
