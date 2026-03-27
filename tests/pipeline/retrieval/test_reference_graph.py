"""Tests for the artist reference graph (position weights, build, save/load)."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.domain.models import Review
from music_review.io.jsonl import write_jsonl
from music_review.io.reviews_jsonl import save_reviews_to_jsonl
from music_review.pipeline.retrieval.reference_graph import (
    attribute_purity_summary,
    build_artist_attribute_profiles,
    build_artist_graph,
    load_graph,
    position_weight,
    reference_community_position_masses,
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


def test_reference_community_position_masses_two_refs() -> None:
    """Masses match position_weight per referenced artist community."""
    review = Review(
        id=1,
        url="u",
        artist="A",
        album="B",
        text="t",
        references=["X", "Y"],
    )
    memberships = {
        "x": {"res_10": "C1"},
        "y": {"res_10": "C2"},
    }
    m = reference_community_position_masses(
        review,
        memberships,
        res_key="res_10",
        w_min=0.2,
    )
    assert m["C1"] == pytest.approx(1.0)
    assert m["C2"] == pytest.approx(0.2)


def test_reference_community_position_masses_empty_refs() -> None:
    review = Review(id=1, url="u", artist="A", album="B", text="t", references=[])
    assert (
        reference_community_position_masses(
            review,
            {"x": {"res_10": "C1"}},
            res_key="res_10",
        )
        == {}
    )


def test_build_artist_graph_position_averaging(tmp_path: Path) -> None:
    """Edge weight is average over albums: ref only in one of two albums -> 0.5."""
    # Artist A:
    # Album1 references X first (1.0), Album2 does not reference X (0.0) -> avg 0.5
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
        Review(
            id=1,
            url="u1",
            artist="Tweedy",
            album="A",
            text="t",
            references=["Wilco"],
        ),
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


def test_build_artist_attribute_profiles_aggregates_review_and_metadata(
    tmp_path: Path,
) -> None:
    """Artist profiles aggregate authors, labels, year buckets, and metadata genres."""
    reviews = [
        Review(
            id=1,
            url="u1",
            artist="A",
            album="Album1",
            text="t",
            author="Alice",
            release_year=2001,
            labels=["Matador"],
        ),
        Review(
            id=2,
            url="u2",
            artist="A",
            album="Album2",
            text="t",
            author="Alice",
            release_year=2003,
            labels=["Domino"],
        ),
        Review(
            id=3,
            url="u3",
            artist="B",
            album="Album3",
            text="t",
            author="Bob",
            release_year=2011,
            labels=["Warp"],
        ),
    ]
    reviews_path = tmp_path / "reviews.jsonl"
    save_reviews_to_jsonl(reviews, reviews_path)

    metadata_path = tmp_path / "metadata.jsonl"
    write_jsonl(
        metadata_path,
        [
            {"review_id": 1, "genres": ["Indie Rock", "Lo-Fi"]},
            {"review_id": 2, "genres": ["Indie Rock"]},
            {"review_id": 3, "genres": ["Electronic"]},
        ],
    )

    profiles = build_artist_attribute_profiles(
        reviews_path,
        metadata_path=metadata_path,
    )
    assert profiles["a"]["authors"]["Alice"] == 2
    assert profiles["a"]["labels"]["Matador"] == 1
    assert profiles["a"]["labels"]["Domino"] == 1
    assert profiles["a"]["year_buckets"]["2000-2004"] == 2
    assert profiles["a"]["genres"]["Indie Rock"] == 2
    assert profiles["a"]["genres"]["Lo-Fi"] == 1
    assert profiles["b"]["genres"]["Electronic"] == 1


def test_attribute_purity_summary_reports_expected_scores() -> None:
    """Attribute purity is high when each community has a clear dominant value."""
    communities = [frozenset({"a", "b"}), frozenset({"c"})]
    profiles = {
        "a": {
            "genres": {"Indie Rock": 2},
            "authors": {"Alice": 2},
            "year_buckets": {"2000-2004": 2},
            "labels": {"Matador": 2},
        },
        "b": {
            "genres": {"Indie Rock": 1, "Post-Punk": 1},
            "authors": {"Alice": 1},
            "year_buckets": {"2000-2004": 1},
            "labels": {"Domino": 1},
        },
        "c": {
            "genres": {"Electronic": 2},
            "authors": {"Bob": 2},
            "year_buckets": {"2010-2014": 2},
            "labels": {"Warp": 2},
        },
    }

    summary = attribute_purity_summary(communities, profiles)
    assert summary["genre_purity"] == pytest.approx(5 / 6)
    assert summary["author_purity"] == pytest.approx(1.0)
    assert summary["year_purity"] == pytest.approx(1.0)
    assert summary["label_purity"] == pytest.approx(4 / 5)
    assert summary["combined_attribute_purity"] == pytest.approx(
        ((5 / 6) + 1.0 + 1.0 + (4 / 5)) / 4
    )
