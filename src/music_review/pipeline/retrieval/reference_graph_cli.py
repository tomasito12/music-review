"""CLI for artist reference graph and community analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from music_review.config import REFERENCE_POSITION_W_MIN, resolve_data_path
from music_review.pipeline.retrieval.reference_graph import (
    attribute_purity_summary,
    build_artist_attribute_profiles,
    build_artist_graph,
    compute_album_affinities,
    detect_communities,
    export_communities_incremental,
    export_fixed_clusterings,
    load_artist_communities,
    previous_memberships_usable,
    resolution_to_res_key,
    save_graph,
    to_undirected_weighted,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: build artist graph from reviews and save to data/."""
    args = _build_parser().parse_args(argv)

    if not args.reviews.exists():
        print(f"Error: reviews file not found: {args.reviews}", file=sys.stderr)
        return 1

    G = build_artist_graph(args.reviews, w_min=args.w_min)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_graph(G, args.output)
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
    print(f"Saved to {args.output}")

    if args.scan_resolutions:
        rc = _run_resolution_scan(G, args)
        if rc != 0:
            return rc

    export_resolutions = _run_community_export(G, args)

    if args.export_album_affinities:
        _run_album_affinities(args, export_resolutions)

    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build argument parser for the graph-build CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Build artist reference graph from reviews.jsonl (weighted by position)."
        ),
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
        default=REFERENCE_POSITION_W_MIN,
        help=(
            "Minimum weight for last reference in a list "
            f"(default {REFERENCE_POSITION_W_MIN})."
        ),
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
            "clusterings for (e.g. '10'). Writes communities_res_{res}.json "
            "and community_memberships.jsonl in the data directory."
        ),
    )
    parser.add_argument(
        "--communities-mode",
        choices=("incremental", "louvain"),
        default="incremental",
        help=(
            "incremental: keep existing community IDs from --previous-memberships "
            "and assign new artists via the graph (default). "
            "louvain: full re-cluster (new C00x IDs; rerun community_genre_labels)."
        ),
    )
    parser.add_argument(
        "--previous-memberships",
        type=Path,
        default=None,
        help=(
            "For incremental mode: path to community_memberships.jsonl "
            "(default: data/community_memberships.jsonl)."
        ),
    )
    parser.add_argument(
        "--export-album-affinities",
        action="store_true",
        help=(
            "If set, compute soft album-community affinities based on references "
            "and write them to data/album_community_affinities.jsonl. "
            "Uses resolutions from --export-communities or defaults to 10."
        ),
    )
    return parser


def _parse_float_list(raw: str) -> list[float] | None:
    """Parse comma-separated floats. Returns None on invalid input."""
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    try:
        return sorted({float(s) for s in parts})
    except ValueError:
        return None


def _run_resolution_scan(
    G: Any,  # nx.DiGraph
    args: argparse.Namespace,
) -> int:
    """Run modularity + attribute purity scan over resolutions."""
    from networkx.algorithms.community.quality import modularity

    gammas = _parse_float_list(args.scan_resolutions)
    if gammas is None:
        print(
            f"Error: invalid --scan-resolutions value {args.scan_resolutions!r}",
            file=sys.stderr,
        )
        return 1
    if not gammas:
        print("No valid resolution values provided for scan.", file=sys.stderr)
        return 1

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
        q = modularity(
            to_undirected_weighted(G, weight="weight"),
            communities,
            weight="weight",
            resolution=gamma,
        )
        sizes = [len(c) for c in communities]
        comm_index: dict[str, int] = {}
        for idx, comm in enumerate(communities):
            for n in comm:
                comm_index[n] = idx
        internal_w = sum(
            float(data.get("weight", 1.0))
            for u, _, data in G.edges(data=True)
            if comm_index.get(u) == comm_index.get(_)
        )
        external_w = max(total_weight - internal_w, 0.0)
        attr_summary = attribute_purity_summary(communities, profiles)
        num_comms = len(communities)
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
                "internal_share": (internal_w / total_weight if total_weight else 0.0),
                "external_share": (external_w / total_weight if total_weight else 0.0),
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
    return 0


def _run_community_export(
    G: Any,  # nx.DiGraph
    args: argparse.Namespace,
) -> list[float]:
    """Export community clusterings if requested. Returns the export resolutions."""
    if not args.export_communities:
        return []

    export_resolutions = _parse_float_list(args.export_communities)
    if export_resolutions is None:
        print(
            f"Error: invalid --export-communities value {args.export_communities!r}",
            file=sys.stderr,
        )
        return []
    if not export_resolutions:
        print(
            "No valid resolution values provided for export-communities.",
            file=sys.stderr,
        )
        return []

    data_dir = resolve_data_path("data")
    prev_path = (
        args.previous_memberships
        if args.previous_memberships is not None
        else data_dir / "community_memberships.jsonl"
    )
    res_keys = [resolution_to_res_key(r) for r in export_resolutions]
    previous = load_artist_communities(prev_path)
    use_incremental = (
        args.communities_mode == "incremental"
        and prev_path.exists()
        and previous_memberships_usable(previous, res_keys)
    )

    if args.communities_mode == "louvain":
        print(
            "WARNING: Louvain recluster — community C00x IDs will change. "
            "Regenerate data/community_genre_labels_res_*.json after this.",
            file=sys.stderr,
        )
    elif args.communities_mode == "incremental" and not use_incremental:
        print(
            "WARNING: No usable previous memberships at "
            f"{prev_path}; falling back to Louvain once. "
            "Next run will use incremental mode.",
            file=sys.stderr,
        )

    if use_incremental:
        print(
            f"Exporting incremental clusterings for {export_resolutions} "
            f"into {data_dir} (stable IDs from {prev_path})"
        )
        export_communities_incremental(
            G,
            export_resolutions,
            data_dir,
            prev_path,
        )
    else:
        print(
            f"Exporting Louvain clusterings for resolutions {export_resolutions} "
            f"into {data_dir}"
        )
        export_fixed_clusterings(G, export_resolutions, data_dir)

    return export_resolutions


def _run_album_affinities(
    args: argparse.Namespace,
    export_resolutions: list[float],
) -> None:
    """Compute and write album-community affinities."""
    data_dir = resolve_data_path("data")
    memberships_path = data_dir / "community_memberships.jsonl"
    resolutions = export_resolutions if export_resolutions else [10.0]
    print(
        "Computing album→community affinities for resolutions "
        f"{resolutions} using {memberships_path}"
    )
    affinities = compute_album_affinities(
        reviews_path=args.reviews,
        memberships_path=memberships_path,
        resolutions=resolutions,
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


if __name__ == "__main__":
    raise SystemExit(main())
