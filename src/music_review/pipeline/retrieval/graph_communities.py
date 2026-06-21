"""Louvain community detection and graph distance helpers."""

from __future__ import annotations

import networkx as nx

from music_review.pipeline.retrieval.graph_build import to_undirected_weighted


def detect_communities(
    G: nx.DiGraph,
    weight: str = "weight",
    resolution: float = 1.0,
) -> list[frozenset[str]]:
    """Run Louvain community detection on the graph (undirected, weighted).

    Returns a list of communities, each a frozenset of node ids (normalized names).
    """
    U = to_undirected_weighted(G, weight=weight)
    communities = nx.community.louvain_communities(
        U,
        weight=weight,
        resolution=resolution,
    )
    return list(communities)


def community_centroid(
    G: nx.DiGraph,
    node_set: set[str] | frozenset[str],
    weight: str = "weight",
) -> str | None:
    """Return the node in node_set with highest total edge weight (in + out)."""
    if not node_set:
        return None
    best_node: str | None = None
    best_deg: float = -1.0
    for n in node_set:
        if n not in G:
            continue
        deg = G.out_degree(n, weight=weight) + G.in_degree(n, weight=weight)
        if deg > best_deg:
            best_deg = deg
            best_node = n
    return best_node


def distance_between_communities(
    G: nx.DiGraph,
    set1: set[str] | frozenset[str],
    set2: set[str] | frozenset[str],
    method: str = "min",
) -> float | None:
    """Shortest-path distance between two node sets (undirected, unweighted hops).

    method: 'min' = minimum pairwise distance, 'avg' = average pairwise distance.
    Returns None if no path exists (disconnected).
    """
    U = G.to_undirected()
    distances: list[float] = []
    for s in set1:
        if s not in U:
            continue
        try:
            lengths = nx.single_source_shortest_path_length(U, s)
        except Exception:
            continue
        for t in set2:
            if t not in lengths:
                continue
            distances.append(float(lengths[t]))
    if not distances:
        return None
    if method == "min":
        return min(distances)
    return sum(distances) / len(distances)


def centroid_distance_between_communities(
    G: nx.DiGraph,
    comm1: set[str] | frozenset[str],
    comm2: set[str] | frozenset[str],
    cutoff: int = 10,
) -> float | None:
    """Shortest-path distance (in hops) between community centroids.

    Uses the centroid (highest weighted degree) of each community as a
    representative node and computes the shortest path between them in the
    undirected version of the graph. Returns None if no path exists within
    the given cutoff radius.
    """
    if not comm1 or not comm2:
        return None
    U = G.to_undirected()
    src = community_centroid(G, set(comm1), weight="weight")
    tgt = community_centroid(G, set(comm2), weight="weight")
    if src is None or tgt is None or src not in U or tgt not in U:
        return None
    try:
        lengths = nx.single_source_shortest_path_length(U, src, cutoff=cutoff)
    except Exception:
        return None
    if tgt not in lengths:
        return None
    return float(lengths[tgt])


def community_distance_matrix(
    G: nx.DiGraph,
    communities: list[frozenset[str]],
    method: str = "min",
) -> list[list[float | None]]:
    """Pairwise distance between communities via centroids.

    Uses shortest-path distance between community centroids (in undirected graph).
    Returns an NxN matrix (None = disconnected). method is reserved for future
    extensions and currently ignored.
    """
    n = len(communities)
    matrix: list[list[float | None]] = [[None] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 0.0
    if n == 0:
        return matrix

    U = G.to_undirected()
    centroids: list[str | None] = [
        community_centroid(G, set(comm), weight="weight") for comm in communities
    ]

    # For each centroid, run a BFS once (cut off at a reasonable radius)
    for i, src in enumerate(centroids):
        if src is None or src not in U:
            continue
        try:
            lengths = nx.single_source_shortest_path_length(U, src, cutoff=10)
        except Exception:
            continue
        for j, tgt in enumerate(centroids):
            if tgt is None or tgt not in lengths:
                continue
            d = float(lengths[tgt])
            if matrix[i][j] is None or d < (matrix[i][j] or 0):
                matrix[i][j] = matrix[j][i] = d
    return matrix
