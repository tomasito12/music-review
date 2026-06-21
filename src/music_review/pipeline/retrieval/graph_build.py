"""Build and persist the artist reference graph and attribute profiles."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from music_review.config import REFERENCE_POSITION_W_MIN
from music_review.domain.reference_masses import (
    normalize_reference_artist_name,
    position_weight,
)
from music_review.io.jsonl import load_jsonl_as_map
from music_review.io.reviews_jsonl import load_reviews_from_jsonl


def build_artist_graph(
    reviews_path: str | Path,
    w_min: float = REFERENCE_POSITION_W_MIN,
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
        anorm = normalize_reference_artist_name(r.artist)
        if not anorm:
            continue
        norm_to_display[anorm] = r.artist.strip() or anorm
        refs = [ref for ref in (r.references or []) if ref and isinstance(ref, str)]
        artist_albums[anorm].append(refs)
        for ref in refs:
            rnorm = normalize_reference_artist_name(ref)
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
                rnorm = normalize_reference_artist_name(ref)
                if rnorm:
                    all_tgts.add(rnorm)
        for tgt_norm in all_tgts:
            total = 0.0
            for ref_list in albums:
                n = len(ref_list)
                # Find position of tgt in this album (first occurrence)
                pos = 0
                for i, ref in enumerate(ref_list):
                    if normalize_reference_artist_name(ref) == tgt_norm:
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
        artist_key = normalize_reference_artist_name(review.artist)
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


def save_graph(G: nx.DiGraph, path: str | Path) -> None:
    """Write the graph to a GraphML file (preserves node/edge attributes)."""
    nx.write_graphml(G, Path(path))


def load_graph(path: str | Path) -> nx.DiGraph:
    """Load a directed graph from a GraphML file (e.g. saved by save_graph)."""
    G = nx.read_graphml(Path(path))
    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    # GraphML may read edge weight as string
    for _u, _v, data in G.edges(data=True):
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
