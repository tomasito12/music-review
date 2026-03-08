# music_review/pipeline/retrieval/reference_graph.py

"""Artist reference graph: weighted directed edges from album artists to referenced artists."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import networkx as nx

from music_review.io.reviews_jsonl import load_reviews_from_jsonl


def _normalize_name(name: str) -> str:
    """Normalize artist name for node identity (lowercase, strip)."""
    return name.strip().lower() if name else ""


def position_weight(
    position_1based: int,
    num_references: int,
    w_min: float = 0.2,
) -> float:
    """Weight for a reference by its position in the album's reference list.

    First reference gets 1.0, last gets w_min (never 0). Linear decay in between.

    Args:
        position_1based: 1-based index (1 = first reference).
        num_references: Total number of references in that album.
        w_min: Minimum weight for the last position (e.g. 0.2).

    Returns:
        Weight in [w_min, 1.0].
    """
    if num_references <= 0:
        return w_min
    if num_references == 1:
        return 1.0
    # Linear: first = 1.0, last = w_min
    return w_min + (1.0 - w_min) * (num_references - position_1based) / (
        num_references - 1
    )


def build_artist_graph(
    reviews_path: str | Path,
    w_min: float = 0.2,
) -> nx.DiGraph:
    """Build a directed artist graph from reviews JSONL.

    Nodes are normalized artist names (lowercase, strip). Edges go from the
    album artist to each referenced artist. Edge weight is the average over
    all albums of that artist: for each album, contribution is the position-based
    weight if the target is referenced, else 0.

    Node attribute "display_name" holds a canonical display string (first
    occurrence from the data).

    Args:
        reviews_path: Path to reviews.jsonl.
        w_min: Minimum position weight for the last reference in a list.

    Returns:
        NetworkX DiGraph with "weight" on edges and "display_name" on nodes.
    """
    path = Path(reviews_path)
    reviews = load_reviews_from_jsonl(path)

    # artist_norm -> list of reference lists (one list per album, refs in order)
    artist_albums: dict[str, list[list[str]]] = defaultdict(list)
    norm_to_display: dict[str, str] = {}

    for r in reviews:
        anorm = _normalize_name(r.artist)
        if not anorm:
            continue
        norm_to_display[anorm] = r.artist.strip() or anorm
        refs = [ref for ref in (r.references or []) if ref and isinstance(ref, str)]
        artist_albums[anorm].append(refs)
        for ref in refs:
            rnorm = _normalize_name(ref)
            if rnorm:
                norm_to_display[rnorm] = ref.strip() or rnorm

    # For each (src, tgt), compute average weight over all albums of src
    # (0 if tgt not referenced in that album)
    edge_weights: dict[tuple[str, str], float] = {}

    for artist_norm, albums in artist_albums.items():
        n_albums = len(albums)
        if n_albums == 0:
            continue
        # All possible targets that appear in any album of this artist
        all_tgts: set[str] = set()
        for ref_list in albums:
            for ref in ref_list:
                rnorm = _normalize_name(ref)
                if rnorm:
                    all_tgts.add(rnorm)
        for tgt_norm in all_tgts:
            total = 0.0
            for ref_list in albums:
                n = len(ref_list)
                # Find position of tgt in this album (first occurrence)
                pos = 0
                for i, ref in enumerate(ref_list):
                    if _normalize_name(ref) == tgt_norm:
                        pos = i + 1
                        break
                if pos > 0:
                    total += position_weight(pos, n, w_min)
                # else: contribution 0 for this album
            avg = total / n_albums
            edge_weights[(artist_norm, tgt_norm)] = avg

    G = nx.DiGraph()
    for (src, tgt), w in edge_weights.items():
        if w <= 0:
            continue
        G.add_edge(src, tgt, weight=w)
    for n in G.nodes():
        if n not in norm_to_display:
            norm_to_display[n] = n
        G.nodes[n]["display_name"] = norm_to_display[n]

    return G


def save_graph(G: nx.DiGraph, path: str | Path) -> None:
    """Write the graph to a GraphML file (preserves node/edge attributes)."""
    nx.write_graphml(G, Path(path))


def load_graph(path: str | Path) -> nx.DiGraph:
    """Load a directed graph from a GraphML file (e.g. saved by save_graph)."""
    G = nx.read_graphml(Path(path))
    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    # GraphML may read edge weight as string
    for u, v, data in G.edges(data=True):
        if "weight" in data and isinstance(data["weight"], str):
            data["weight"] = float(data["weight"])
    return G


def _main() -> int:
    """CLI: build artist graph from reviews and save to data/."""
    import argparse
    import sys

    from music_review.config import resolve_data_path

    parser = argparse.ArgumentParser(
        description="Build artist reference graph from reviews.jsonl (weighted by position).",
    )
    parser.add_argument(
        "--reviews",
        type=Path,
        default=resolve_data_path("data/reviews.jsonl"),
        help="Path to reviews.jsonl.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=resolve_data_path("data/artist_reference_graph.graphml"),
        help="Output GraphML path.",
    )
    parser.add_argument(
        "--w-min",
        type=float,
        default=0.2,
        help="Minimum weight for last reference in a list (default 0.2).",
    )
    args = parser.parse_args()

    if not args.reviews.exists():
        print(f"Error: reviews file not found: {args.reviews}", file=sys.stderr)
        return 1

    G = build_artist_graph(args.reviews, w_min=args.w_min)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_graph(G, args.output)
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"Saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
