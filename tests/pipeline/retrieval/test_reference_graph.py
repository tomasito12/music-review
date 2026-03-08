"""Tests for the artist reference graph (position weights, build, save/load)."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.domain.models import Review
from music_review.io.reviews_jsonl import save_reviews_to_jsonl
from music_review.pipeline.retrieval.reference_graph import (
    build_artist_graph,
    load_graph,
    position_weight,
    save_graph,
)


def test_position_weight_single_reference() -> None:
    """Single reference gets weight 1.0."""
    assert position_weight(1, 1) == 1.0
    assert position_weight(1, 1, w_min=0.2) == 1.0


def test_position_weight_first_and_last() -> None:
    """First position 1.0, last position w_min (linear)."""
    assert position_weight(1, 3, w_min=0.2) == pytest.approx(1.0)
    assert position_weight(3, 3, w_min=0.2) == 0.2
    assert position_weight(2, 3, w_min=0.2) == pytest.approx(0.6)


def test_position_weight_custom_w_min() -> None:
    """Custom w_min is used for last position."""
    assert position_weight(2, 2, w_min=0.5) == 0.5
    assert position_weight(1, 2, w_min=0.5) == 1.0


def test_position_weight_zero_refs_returns_w_min() -> None:
    """No references: return w_min."""
    assert position_weight(1, 0, w_min=0.2) == 0.2


def test_build_artist_graph_position_averaging(tmp_path: Path) -> None:
    """Edge weight is average over albums: ref only in one of two albums -> 0.5."""
    # Artist A: Album1 references X first (1.0), Album2 does not reference X (0.0) -> avg 0.5
    reviews = [
        Review(id=1, url="u1", artist="A", album="Album1", text="t", references=["X"]),
        Review(id=2, url="u2", artist="A", album="Album2", text="t", references=[]),
    ]
    path = tmp_path / "reviews.jsonl"
    save_reviews_to_jsonl(reviews, path)
    G = build_artist_graph(path, w_min=0.2)
    assert G.has_edge("a", "x")
    assert G.edges["a", "x"]["weight"] == pytest.approx(0.5)


def test_build_artist_graph_normalized_nodes(tmp_path: Path) -> None:
    """Nodes are normalized (lowercase); display_name keeps first occurrence."""
    reviews = [
        Review(id=1, url="u1", artist="Tweedy", album="A", text="t", references=["Wilco"]),
    ]
    path = tmp_path / "reviews.jsonl"
    save_reviews_to_jsonl(reviews, path)
    G = build_artist_graph(path)
    assert "tweedy" in G.nodes
    assert "wilco" in G.nodes
    assert G.nodes["tweedy"]["display_name"] == "Tweedy"
    assert G.nodes["wilco"]["display_name"] == "Wilco"
    assert G.has_edge("tweedy", "wilco")
    assert G.edges["tweedy", "wilco"]["weight"] == 1.0


def test_build_artist_graph_multi_album_weights(tmp_path: Path) -> None:
    """Two albums: different positions for same target yield averaged weight."""
    # A - Album1: refs [X, Y] -> X=1.0, Y=0.2 (last of 2)
    # A - Album2: refs [Y] -> Y=1.0
    # Edge A->X: (1.0+0)/2 = 0.5. Edge A->Y: (0.2+1.0)/2 = 0.6
    reviews = [
        Review(id=1, url="u1", artist="A", album="1", text="t", references=["X", "Y"]),
        Review(id=2, url="u2", artist="A", album="2", text="t", references=["Y"]),
    ]
    path = tmp_path / "reviews.jsonl"
    save_reviews_to_jsonl(reviews, path)
    G = build_artist_graph(path, w_min=0.2)
    assert G.edges["a", "x"]["weight"] == pytest.approx(0.5)
    assert G.edges["a", "y"]["weight"] == pytest.approx(0.6)


def test_save_and_load_graph_roundtrip(tmp_path: Path) -> None:
    """Save_graph and load_graph preserve nodes, edges, and weight."""
    reviews = [
        Review(id=1, url="u1", artist="A", album="B", text="t", references=["C"]),
    ]
    path = tmp_path / "reviews.jsonl"
    save_reviews_to_jsonl(reviews, path)
    G = build_artist_graph(path)
    out = tmp_path / "graph.graphml"
    save_graph(G, out)
    H = load_graph(out)
    assert H.number_of_nodes() == G.number_of_nodes()
    assert H.number_of_edges() == G.number_of_edges()
    assert H.has_edge("a", "c")
    assert H.edges["a", "c"]["weight"] == pytest.approx(1.0)
    assert H.nodes["a"]["display_name"] == "A"
