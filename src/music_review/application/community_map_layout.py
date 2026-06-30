"""Build a 2D layout for taste-community map views from the reference graph."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import networkx as nx

from music_review.data_access.communities import load_artist_communities
from music_review.data_access.paths import (
    artist_reference_graph_path,
    communities_res_10_path,
    community_memberships_path,
)
from music_review.pipeline.retrieval.graph_build import load_graph

RESOLUTION_KEY = "res_10"
TOP_NEIGHBOR_COUNT = 6
LAYOUT_SEED = 42


@dataclass(frozen=True, slots=True)
class CommunityMapNode:
    """One community position on the style-world map."""

    id: str
    x: float
    y: float
    size: int
    neighbors: tuple[str, ...]


def build_community_map_layout(
    *,
    communities: list[dict[str, Any]] | None = None,
    memberships: dict[str, dict[str, str]] | None = None,
    graph_path: str | None = None,
) -> tuple[CommunityMapNode, ...]:
    """Return normalized map coordinates and top graph neighbors per community."""
    community_rows = communities if communities is not None else _load_communities()
    if not community_rows:
        return ()

    community_ids = [str(item["id"]) for item in community_rows if item.get("id")]
    sizes = {
        str(item["id"]): int(item.get("size") or 1)
        for item in community_rows
        if item.get("id")
    }
    resolved_memberships = (
        memberships if memberships is not None else load_artist_communities()
    )
    neighbor_map = _neighbor_map_for_communities(
        community_ids=community_ids,
        memberships=resolved_memberships,
        graph_path=graph_path,
    )
    positions = _layout_positions(community_ids, neighbor_map)
    return tuple(
        CommunityMapNode(
            id=community_id,
            x=positions[community_id][0],
            y=positions[community_id][1],
            size=max(1, sizes.get(community_id, 1)),
            neighbors=neighbor_map.get(community_id, ()),
        )
        for community_id in community_ids
    )


def _load_communities() -> list[dict[str, Any]]:
    from music_review.data_access.communities import load_communities_res_10

    return load_communities_res_10()


def _neighbor_map_for_communities(
    *,
    community_ids: list[str],
    memberships: dict[str, dict[str, str]],
    graph_path: str | None,
) -> dict[str, tuple[str, ...]]:
    """Map each community id to its strongest cross-community neighbors."""
    allowed = set(community_ids)
    cross_weights: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    graph_file = (
        graph_path if graph_path is not None else str(artist_reference_graph_path())
    )
    try:
        graph = load_graph(graph_file)
    except (OSError, ValueError):
        return {community_id: () for community_id in community_ids}

    for source, target, data in graph.edges(data=True):
        source_community = _artist_community_id(source, memberships)
        target_community = _artist_community_id(target, memberships)
        if (
            source_community is None
            or target_community is None
            or source_community == target_community
            or source_community not in allowed
            or target_community not in allowed
        ):
            continue
        weight = float(data.get("weight", 1.0))
        cross_weights[source_community][target_community] += weight
        cross_weights[target_community][source_community] += weight

    return {
        community_id: _top_neighbors(cross_weights.get(community_id, {}))
        for community_id in community_ids
    }


def _artist_community_id(
    artist_id: str,
    memberships: dict[str, dict[str, str]],
) -> str | None:
    """Return the resolution-10 community id for one artist, if known."""
    row = memberships.get(artist_id)
    if row is None:
        return None
    community_id = row.get(RESOLUTION_KEY)
    if not isinstance(community_id, str) or not community_id.strip():
        return None
    return community_id.strip()


def _top_neighbors(weights: dict[str, float]) -> tuple[str, ...]:
    """Return the strongest neighbor ids for one community."""
    ranked = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    return tuple(neighbor_id for neighbor_id, _weight in ranked[:TOP_NEIGHBOR_COUNT])


def _layout_positions(
    community_ids: list[str],
    neighbor_map: dict[str, tuple[str, ...]],
) -> dict[str, tuple[float, float]]:
    """Compute normalized x/y positions for all communities."""
    if not community_ids:
        return {}

    graph = nx.Graph()
    for community_id in community_ids:
        graph.add_node(community_id)
    for community_id, neighbors in neighbor_map.items():
        for neighbor_id in neighbors:
            if graph.has_node(neighbor_id):
                graph.add_edge(community_id, neighbor_id, weight=1.0)

    if graph.number_of_edges() == 0:
        raw_positions = _circular_layout(community_ids)
    else:
        raw_positions = nx.spring_layout(
            graph,
            seed=LAYOUT_SEED,
            k=0.55,
            iterations=75,
            weight="weight",
        )
    return _normalize_positions(raw_positions)


def _circular_layout(community_ids: list[str]) -> dict[str, tuple[float, float]]:
    """Place communities on a circle when no graph edges are available."""
    import math

    sorted_ids = sorted(community_ids)
    count = len(sorted_ids)
    if count == 1:
        return {sorted_ids[0]: (0.0, 0.0)}
    positions: dict[str, tuple[float, float]] = {}
    for index, community_id in enumerate(sorted_ids):
        angle = (2.0 * math.pi * index) / count
        positions[community_id] = (math.cos(angle), math.sin(angle))
    return positions


def _normalize_positions(
    positions: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """Scale positions into the 0..1 range with a small margin."""
    if not positions:
        return {}
    xs = [point[0] for point in positions.values()]
    ys = [point[1] for point in positions.values()]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    margin = 0.08
    usable = 1.0 - (2.0 * margin)
    return {
        community_id: (
            margin + usable * ((point[0] - min_x) / span_x),
            margin + usable * ((point[1] - min_y) / span_y),
        )
        for community_id, point in positions.items()
    }


def community_map_source_mtimes() -> tuple[float, ...]:
    """Return mtimes for files that invalidate a cached community map layout."""
    paths = (
        artist_reference_graph_path(),
        community_memberships_path(),
        communities_res_10_path(),
    )
    return tuple(path.stat().st_mtime if path.is_file() else 0.0 for path in paths)
