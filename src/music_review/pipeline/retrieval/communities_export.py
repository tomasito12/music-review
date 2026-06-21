"""Export Louvain and incremental community clusterings to JSON artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from music_review.data_access.communities import load_artist_communities
from music_review.pipeline.retrieval.graph_communities import (
    community_centroid,
    detect_communities,
)


def export_fixed_clusterings(
    G: nx.DiGraph,
    resolutions: list[float],
    output_dir: Path,
    top_k: int = 10,
) -> None:
    """Export fixed clusterings for given resolutions and artist memberships.

    For each resolution, writes communities_res_{res}.json with:
        {
          "resolution": <float>,
          "communities": [
            {
              "id": "C001",
              "size": 123,
              "centroid_id": "radiohead",
              "centroid": "Radiohead",
              "top_artists": [...],
              "artists": [...]
            },
            ...
          ]
        }

    Additionally writes community_memberships.jsonl mapping each artist to
    its community IDs per resolution (keys like "res_10", ...).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    def display_name(node: str) -> str:
        value = G.nodes[node].get("display_name") if node in G.nodes else None
        return str(value).strip() if value else node

    artist_memberships: dict[str, dict[str, str]] = defaultdict(dict)

    for resolution in resolutions:
        communities = detect_communities(G, weight="weight", resolution=resolution)
        communities_sorted = sorted(communities, key=len, reverse=True)
        clusters: list[dict[str, Any]] = []

        res_key = (
            f"res_{int(resolution)}"
            if float(resolution).is_integer()
            else f"res_{resolution}"
        )

        for idx, comm in enumerate(communities_sorted):
            cid = f"C{idx + 1:03d}"
            nodes = list(comm)
            size = len(nodes)
            centroid_id = community_centroid(G, comm, weight="weight")
            centroid_name = display_name(centroid_id) if centroid_id else ""

            # Top artists by weighted degree (in + out)
            top_nodes = sorted(
                nodes,
                key=lambda n: (
                    G.out_degree(n, weight="weight") + G.in_degree(n, weight="weight")
                ),
                reverse=True,
            )[:top_k]

            cluster_obj: dict[str, Any] = {
                "id": cid,
                "size": size,
                "centroid_id": centroid_id,
                "centroid": centroid_name,
                "top_artists": [display_name(n) for n in top_nodes],
                "artists": [display_name(n) for n in nodes],
            }
            clusters.append(cluster_obj)

            for n in nodes:
                artist_memberships[n][res_key] = cid

        res_name = (
            str(int(resolution))
            if float(resolution).is_integer()
            else str(resolution).replace(".", "_")
        )
        communities_path = output_dir / f"communities_res_{res_name}.json"
        with communities_path.open("w", encoding="utf-8") as f:
            json.dump(
                {"resolution": float(resolution), "communities": clusters},
                f,
                ensure_ascii=False,
                indent=2,
            )

    # Write artist -> community memberships
    memberships_path = output_dir / "community_memberships.jsonl"
    with memberships_path.open("w", encoding="utf-8") as f:
        for artist_id, mapping in sorted(artist_memberships.items()):
            obj = {
                "artist_id": artist_id,
                "artist": display_name(artist_id),
                "communities": mapping,
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def resolution_to_res_key(resolution: float) -> str:
    """JSON key for a Louvain resolution (e.g. 10.0 -> res_10)."""
    if float(resolution).is_integer():
        return f"res_{int(resolution)}"
    return f"res_{resolution}"


def merge_memberships_incremental(
    G: nx.DiGraph,
    previous: dict[str, dict[str, str]],
    res_key: str,
) -> dict[str, str]:
    """Stable community ID per artist for one resolution.

    Keeps the previous community for every node still in the graph. New nodes
    pick a community via weighted votes on out-edges (artist -> reference), using
    edge weights from the graph. Votes propagate in rounds until no new
    assignments (multi-hop). Nodes that never connect to an assigned artist are
    omitted (no ``res_key`` in the exported memberships).
    """
    assignment: dict[str, str] = {}
    for n in G.nodes:
        prev_row = previous.get(n, {})
        cid = prev_row.get(res_key)
        if isinstance(cid, str) and cid.strip():
            assignment[n] = cid.strip()

    max_rounds = len(G.nodes) + 2
    for _ in range(max_rounds):
        changed = False
        for n in G.nodes:
            if n in assignment:
                continue
            votes: dict[str, float] = defaultdict(float)
            for _u, t, data in G.out_edges(n, data=True):
                w = data.get("weight", 1.0)
                if isinstance(w, str):
                    w = float(w)
                if t in assignment:
                    votes[assignment[t]] += float(w)
            if votes:
                best_cid, _w = max(votes.items(), key=lambda item: (item[1], item[0]))
                assignment[n] = best_cid
                changed = True
        if not changed:
            break

    return assignment


def _write_communities_res_json(
    G: nx.DiGraph,
    resolution: float,
    assignment: dict[str, str],
    output_dir: Path,
    top_k: int,
) -> None:
    """Write ``communities_res_<res>.json`` from stable community IDs (sorted by id)."""

    def display_name(node: str) -> str:
        value = G.nodes[node].get("display_name") if node in G.nodes else None
        return str(value).strip() if value else node

    by_cid: dict[str, list[str]] = defaultdict(list)
    for artist_id, cid in assignment.items():
        by_cid[cid].append(artist_id)

    clusters: list[dict[str, Any]] = []
    for cid in sorted(by_cid.keys()):
        nodes = by_cid[cid]
        node_set = frozenset(nodes)
        centroid_id = community_centroid(G, node_set, weight="weight")
        centroid_name = display_name(centroid_id) if centroid_id else ""
        top_nodes = sorted(
            nodes,
            key=lambda n: (
                G.out_degree(n, weight="weight") + G.in_degree(n, weight="weight")
            ),
            reverse=True,
        )[:top_k]
        clusters.append(
            {
                "id": cid,
                "size": len(nodes),
                "centroid_id": centroid_id,
                "centroid": centroid_name,
                "top_artists": [display_name(n) for n in top_nodes],
                "artists": sorted(display_name(n) for n in nodes),
            }
        )

    res_name = (
        str(int(resolution))
        if float(resolution).is_integer()
        else str(resolution).replace(".", "_")
    )
    communities_path = output_dir / f"communities_res_{res_name}.json"
    with communities_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"resolution": float(resolution), "communities": clusters},
            f,
            ensure_ascii=False,
            indent=2,
        )


def _write_memberships_jsonl_from_rows(
    G: nx.DiGraph,
    membership_by_artist: dict[str, dict[str, str]],
    output_dir: Path,
) -> None:
    """Write ``community_memberships.jsonl`` for all nodes in ``G``."""

    def display_name(node: str) -> str:
        value = G.nodes[node].get("display_name") if node in G.nodes else None
        return str(value).strip() if value else node

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "community_memberships.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for artist_id in sorted(membership_by_artist.keys()):
            if artist_id not in G.nodes:
                continue
            obj = {
                "artist_id": artist_id,
                "artist": display_name(artist_id),
                "communities": membership_by_artist[artist_id],
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def export_communities_incremental(
    G: nx.DiGraph,
    resolutions: list[float],
    output_dir: Path,
    previous_path: Path,
    top_k: int = 10,
) -> None:
    """Export communities and memberships without re-running Louvain.

    Merges ``previous_path`` memberships with the current graph: existing
    artists keep their community IDs; new artists are assigned via graph-based
    propagation. Writes one ``communities_res_*.json`` per resolution and a
    single ``community_memberships.jsonl``.
    """
    previous = load_artist_communities(previous_path)
    merged_rows: dict[str, dict[str, str]] = {}
    for n in G.nodes:
        merged_rows[n] = dict(previous.get(n, {}))

    for resolution in resolutions:
        res_key = resolution_to_res_key(resolution)
        assignment = merge_memberships_incremental(G, previous, res_key)
        for n in G.nodes:
            merged_rows[n].pop(res_key, None)
        for n, cid in assignment.items():
            merged_rows[n][res_key] = cid
        _write_communities_res_json(G, resolution, assignment, output_dir, top_k)

    _write_memberships_jsonl_from_rows(G, merged_rows, output_dir)


def previous_memberships_usable(
    previous: dict[str, dict[str, str]],
    res_keys: list[str],
) -> bool:
    """True if at least one stored row has a non-empty community for a res key."""
    for row in previous.values():
        for rk in res_keys:
            v = row.get(rk)
            if isinstance(v, str) and v.strip():
                return True
    return False
