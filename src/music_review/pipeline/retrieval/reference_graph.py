"""Artist reference graph and community analysis utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json
import networkx as nx

from music_review.io.jsonl import iter_jsonl_objects
from music_review.io.jsonl import load_jsonl_as_map
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


def _year_bucket(year: int, bucket_size: int = 5) -> str:
    """Bucket a year into fixed-width ranges (default: 5-year buckets)."""
    start = (year // bucket_size) * bucket_size
    end = start + bucket_size - 1
    return f"{start}-{end}"


def build_artist_attribute_profiles(
    reviews_path: str | Path,
    metadata_path: str | Path | None = None,
    metadata_fallback_path: str | Path | None = None,
) -> dict[str, dict[str, Counter[str]]]:
    """Aggregate artist-level attribute counts from reviews and metadata.

    Profiles are keyed by normalized artist name and contain counters for:
    `genres`, `authors`, `year_buckets`, and `labels`.
    """
    reviews = load_reviews_from_jsonl(Path(reviews_path))
    metadata_map: dict[int, dict[str, Any]] = {}

    for path in (metadata_path, metadata_fallback_path):
        if path is None:
            continue
        candidate = Path(path)
        if candidate.exists():
            metadata_map = load_jsonl_as_map(
                candidate,
                id_key="review_id",
                log_errors=False,
            )
            break

    profiles: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: {
            "genres": Counter(),
            "authors": Counter(),
            "year_buckets": Counter(),
            "labels": Counter(),
        }
    )

    for review in reviews:
        artist_key = _normalize_name(review.artist)
        if not artist_key:
            continue
        profile = profiles[artist_key]

        if review.author and review.author.strip():
            profile["authors"][review.author.strip()] += 1

        year: int | None = review.release_year
        if year is None and review.release_date is not None:
            year = review.release_date.year
        if year is not None:
            profile["year_buckets"][_year_bucket(year)] += 1

        for label in review.labels:
            if isinstance(label, str) and label.strip():
                profile["labels"][label.strip()] += 1

        meta = metadata_map.get(review.id, {})
        genres = meta.get("genres") if isinstance(meta, dict) else None
        if isinstance(genres, list):
            for genre in genres:
                if isinstance(genre, str) and genre.strip():
                    profile["genres"][genre.strip()] += 1

    return dict(profiles)


def _weighted_purity_for_attribute(
    communities: list[frozenset[str]],
    profiles: dict[str, dict[str, Counter[str]]],
    attribute: str,
) -> tuple[float | None, float]:
    """Return weighted purity and coverage for one attribute across communities."""
    weighted_sum = 0.0
    weighted_total = 0
    covered_artists = 0
    total_artists = sum(len(comm) for comm in communities)

    for community in communities:
        counts: Counter[str] = Counter()
        community_covered = 0
        for artist in community:
            attr_counts = profiles.get(artist, {}).get(attribute, Counter())
            if attr_counts:
                community_covered += 1
                counts.update(attr_counts)
        if community_covered == 0:
            continue
        covered_artists += community_covered
        total = sum(counts.values())
        if total == 0:
            continue
        purity = max(counts.values()) / total
        weighted_sum += purity * total
        weighted_total += total

    purity_value = weighted_sum / weighted_total if weighted_total else None
    coverage = covered_artists / total_artists if total_artists else 0.0
    return purity_value, coverage


def attribute_purity_summary(
    communities: list[frozenset[str]],
    profiles: dict[str, dict[str, Counter[str]]],
) -> dict[str, float | None]:
    """Summarize attribute purity across communities.

    Purity is the weighted average of each community's dominant-share for the
    given attribute. Coverage is the share of artists with at least one value.
    """
    result: dict[str, float | None] = {}
    attributes = {
        "genre": "genres",
        "author": "authors",
        "year": "year_buckets",
        "label": "labels",
    }

    purity_values: list[float] = []
    for prefix, attr_name in attributes.items():
        purity, coverage = _weighted_purity_for_attribute(
            communities,
            profiles,
            attr_name,
        )
        result[f"{prefix}_purity"] = purity
        result[f"{prefix}_coverage"] = coverage
        if purity is not None:
            purity_values.append(purity)

    result["combined_attribute_purity"] = (
        sum(purity_values) / len(purity_values) if purity_values else None
    )
    return result


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
    its community IDs per resolution (keys like "res_2", "res_6", ...).
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
                key=lambda n: G.out_degree(n, weight="weight")
                + G.in_degree(n, weight="weight"),
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


def compute_album_affinities(
    reviews_path: str | Path,
    memberships_path: str | Path,
    resolutions: list[float],
    w_min: float = 0.2,
    top_k_per_res: int | None = None,
    threshold: float = 0.0,
) -> list[dict[str, Any]]:
    """Compute soft album→community affinities from reference lists.

    For each review, we:
      - take the ordered reference list
      - for each reference and each resolution, look up the artist's community ID
      - add position_weight(i, n, w_min) to that community's score
      - normalise scores per resolution to sum to 1.0
      - optionally drop communities with score below `threshold`
      - optionally keep only top_k_per_res communities

    Returns a list of rows with:
      {
        "review_id": int,
        "artist": str,
        "album": str,
        "url": str,
        "communities": {
          "res_2": [{"id": "C001", "score": 0.62}, ...],
          "res_6": [...],
          "res_10": [...]
        }
      }
    """
    reviews = load_reviews_from_jsonl(Path(reviews_path))

    # Load artist → communities mapping
    memberships: dict[str, dict[str, str]] = {}
    mp = Path(memberships_path)
    if not mp.exists():
        raise FileNotFoundError(f"Memberships file not found: {mp}")
    for obj in iter_jsonl_objects(mp, log_errors=False):
        artist_id = obj.get("artist_id")
        comms = obj.get("communities")
        if isinstance(artist_id, str) and isinstance(comms, dict):
            memberships[artist_id] = {
                str(k): str(v) for k, v in comms.items() if isinstance(v, str)
            }

    rows: list[dict[str, Any]] = []
    res_keys: dict[float, str] = {}
    for res in resolutions:
        if float(res).is_integer():
            res_keys[res] = f"res_{int(res)}"
        else:
            res_keys[res] = f"res_{res}"

    for review in reviews:
        refs = [r for r in review.references if isinstance(r, str) and r.strip()]
        if not refs:
            continue
        n = len(refs)
        res_scores: dict[float, dict[str, float]] = {
            res: {} for res in resolutions
        }

        for idx, ref in enumerate(refs):
            pos = idx + 1
            w = position_weight(pos, n, w_min=w_min)
            artist_key = _normalize_name(ref)
            if not artist_key:
                continue
            artist_comms = memberships.get(artist_key)
            if not artist_comms:
                continue
            for res in resolutions:
                res_key = res_keys[res]
                cid = artist_comms.get(res_key)
                if not cid:
                    continue
                bucket = res_scores[res]
                bucket[cid] = bucket.get(cid, 0.0) + w

        communities_out: dict[str, list[dict[str, Any]]] = {}
        for res in resolutions:
            scores = res_scores[res]
            if not scores:
                continue
            total = sum(scores.values())
            if total <= 0:
                continue
            items = [
                (cid, score / total) for cid, score in scores.items()
            ]
            # Filter by threshold
            if threshold > 0.0:
                items = [item for item in items if item[1] >= threshold]
            if not items:
                continue
            # Sort by score desc
            items.sort(key=lambda x: x[1], reverse=True)
            if top_k_per_res is not None and top_k_per_res > 0:
                items = items[:top_k_per_res]
            key = res_keys[res]
            communities_out[key] = [
                {"id": cid, "score": score} for cid, score in items
            ]

        if not communities_out:
            continue

        rows.append(
            {
                "review_id": review.id,
                "artist": review.artist,
                "album": review.album,
                "url": review.url,
                "communities": communities_out,
            }
        )

    return rows


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


def to_undirected_weighted(G: nx.DiGraph, weight: str = "weight") -> nx.Graph:
    """Build an undirected graph with combined edge weights (sum of both directions)."""
    U = nx.Graph()
    for u, v, data in G.edges(data=True):
        w = data.get(weight)
        if w is None:
            w = 1.0
        elif isinstance(w, str):
            w = float(w)
        if U.has_edge(u, v):
            U.edges[u, v][weight] = U.edges[u, v].get(weight, 0) + w
        else:
            U.add_edge(u, v, **{weight: w})
    # Copy node attributes
    for n in G.nodes():
        if not U.has_node(n):
            U.add_node(n, **dict(G.nodes[n]))
        else:
            U.nodes[n].update(G.nodes[n])
    return U


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
    parser.add_argument(
        "--scan-resolutions",
        type=str,
        default="",
        help=(
            "Optional: comma-separated Louvain resolution values to scan for "
            "modularity, e.g. '0.5,0.75,1.0,1.25,1.5'."
        ),
    )
    parser.add_argument(
        "--scan-output",
        type=Path,
        default=None,
        help=(
            "Optional: output JSON path for resolution scan results. "
            "Defaults to data/community_resolution_scan.json."
        ),
    )
    parser.add_argument(
        "--export-communities",
        type=str,
        default="",
        help=(
            "Optional: comma-separated Louvain resolutions to export fixed "
            "clusterings for (e.g. '2,6,10'). Writes communities_res_{res}.json "
            "and community_memberships.jsonl in the data directory."
        ),
    )
    parser.add_argument(
        "--export-album-affinities",
        action="store_true",
        help=(
            "If set, compute soft album→community affinities based on references "
            "and write them to data/album_community_affinities.jsonl. "
            "Uses resolutions from --export-communities or defaults to 2,6,10."
        ),
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

    if args.scan_resolutions:
        raw = [s.strip() for s in args.scan_resolutions.split(",") if s.strip()]
        try:
            gammas = sorted({float(s) for s in raw})
        except ValueError:
            print(
                f"Error: invalid --scan-resolutions value {args.scan_resolutions!r}",
                file=sys.stderr,
            )
            return 1
        if not gammas:
            print("No valid resolution values provided for scan.", file=sys.stderr)
            return 1

        from networkx.algorithms.community.quality import modularity

        metadata_path = resolve_data_path("data/metadata_imputed.jsonl")
        metadata_fallback_path = resolve_data_path("data/metadata.jsonl")
        profiles = build_artist_attribute_profiles(
            reviews_path=args.reviews,
            metadata_path=metadata_path,
            metadata_fallback_path=metadata_fallback_path,
        )

        print(f"Scanning {len(gammas)} resolution values: {gammas}")
        total_weight = sum(
            float(data.get("weight", 1.0)) for _, _, data in G.edges(data=True)
        )
        results: list[dict[str, Any]] = []
        for gamma in gammas:
            communities = detect_communities(G, weight="weight", resolution=gamma)
            num_comms = len(communities)
            sizes = [len(c) for c in communities]
            q = modularity(
                to_undirected_weighted(G, weight="weight"),
                communities,
                weight="weight",
                resolution=gamma,
            )
            # Internal vs external edge weight
            # Map node -> community index
            comm_index: dict[str, int] = {}
            for idx, comm in enumerate(communities):
                for n in comm:
                    comm_index[n] = idx
            internal_w = 0.0
            for u, v, data in G.edges(data=True):
                w = float(data.get("weight", 1.0))
                if comm_index.get(u) == comm_index.get(v):
                    internal_w += w
            external_w = max(total_weight - internal_w, 0.0)
            attr_summary = attribute_purity_summary(communities, profiles)
            results.append(
                {
                    "resolution": gamma,
                    "modularity": q,
                    "num_communities": num_comms,
                    "num_nodes": G.number_of_nodes(),
                    "num_edges": G.number_of_edges(),
                    "avg_size": sum(sizes) / num_comms if num_comms else 0.0,
                    "min_size": min(sizes) if sizes else 0,
                    "max_size": max(sizes) if sizes else 0,
                    "internal_weight": internal_w,
                    "external_weight": external_w,
                    "internal_share": internal_w / total_weight if total_weight else 0.0,
                    "external_share": external_w / total_weight if total_weight else 0.0,
                    **attr_summary,
                }
            )

        scan_output = (
            args.scan_output
            if args.scan_output is not None
            else resolve_data_path("data/community_resolution_scan.json")
        )
        scan_output.parent.mkdir(parents=True, exist_ok=True)
        with scan_output.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Wrote resolution scan with {len(results)} entries to {scan_output}")

    export_resolutions: list[float] = []
    if args.export_communities:
        raw_res = [s.strip() for s in args.export_communities.split(",") if s.strip()]
        try:
            export_resolutions = sorted({float(s) for s in raw_res})
        except ValueError:
            print(
                f"Error: invalid --export-communities value {args.export_communities!r}",
                file=sys.stderr,
            )
            return 1
        if not export_resolutions:
            print(
                "No valid resolution values provided for export-communities.",
                file=sys.stderr,
            )
            return 1
        data_dir = resolve_data_path("data")
        print(
            f"Exporting fixed clusterings for resolutions {export_resolutions} "
            f"into {data_dir}"
        )
        export_fixed_clusterings(G, export_resolutions, data_dir)

    if args.export_album_affinities:
        data_dir = resolve_data_path("data")
        memberships_path = data_dir / "community_memberships.jsonl"
        if not export_resolutions:
            export_resolutions = [2.0, 6.0, 10.0]
        print(
            "Computing album→community affinities for resolutions "
            f"{export_resolutions} using {memberships_path}"
        )
        affinities = compute_album_affinities(
            reviews_path=args.reviews,
            memberships_path=memberships_path,
            resolutions=export_resolutions,
            w_min=args.w_min,
            top_k_per_res=None,
            threshold=0.0,
        )
        affinities_path = data_dir / "album_community_affinities.jsonl"
        affinities_path.parent.mkdir(parents=True, exist_ok=True)
        with affinities_path.open("w", encoding="utf-8") as f:
            for row in affinities:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            f"Wrote album community affinities for {len(affinities)} reviews to "
            f"{affinities_path}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
