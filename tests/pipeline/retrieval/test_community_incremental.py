"""Tests for incremental (stable) community membership merge and export."""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from music_review.pipeline.retrieval.community_genre_labels import (
    load_communities,
)
from music_review.pipeline.retrieval.reference_graph import (
    export_communities_incremental,
    load_artist_communities,
    merge_memberships_incremental,
    previous_memberships_usable,
    resolution_to_res_key,
)


def test_resolution_to_res_key() -> None:
    assert resolution_to_res_key(10.0) == "res_10"


def test_merge_keeps_previous_cid_when_graph_changes_weights() -> None:
    """Existing nodes keep community even if edge weights change."""
    G = nx.DiGraph()
    G.add_node("a", display_name="A")
    G.add_node("b", display_name="B")
    G.add_edge("a", "b", weight=0.99)
    previous = {
        "a": {"res_10": "C007"},
        "b": {"res_10": "C002"},
    }
    out = merge_memberships_incremental(G, previous, "res_10")
    assert out["a"] == "C007"
    assert out["b"] == "C002"


def test_merge_assigns_new_node_via_reference_edge() -> None:
    G = nx.DiGraph()
    for n, dn in [("a", "A"), ("b", "B"), ("newbie", "New")]:
        G.add_node(n, display_name=dn)
    G.add_edge("a", "b", weight=1.0)
    G.add_edge("newbie", "b", weight=1.0)
    previous = {
        "a": {"res_10": "C001"},
        "b": {"res_10": "C002"},
    }
    out = merge_memberships_incremental(G, previous, "res_10")
    assert out["a"] == "C001"
    assert out["b"] == "C002"
    assert out["newbie"] == "C002"


def test_merge_propagates_second_hop() -> None:
    """New node reaches assigned hub via two reference hops."""
    G = nx.DiGraph()
    for n in ("hub", "mid", "leaf"):
        G.add_node(n, display_name=n)
    G.add_edge("leaf", "mid", weight=1.0)
    G.add_edge("mid", "hub", weight=1.0)
    previous = {"hub": {"res_10": "C099"}}
    out = merge_memberships_incremental(G, previous, "res_10")
    assert out["hub"] == "C099"
    assert out["mid"] == "C099"
    assert out["leaf"] == "C099"


def test_previous_memberships_usable() -> None:
    assert not previous_memberships_usable({}, ["res_10"])
    assert previous_memberships_usable(
        {"x": {"res_10": "C001"}},
        ["res_10"],
    )


def test_load_artist_communities_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    path.write_text(
        json.dumps(
            {
                "artist_id": "foo",
                "artist": "Foo",
                "communities": {"res_10": "C001"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    m = load_artist_communities(path)
    assert m["foo"]["res_10"] == "C001"


def test_export_communities_incremental_writes_jsonl(tmp_path: Path) -> None:
    prev = tmp_path / "prev.jsonl"
    prev.write_text(
        json.dumps(
            {
                "artist_id": "old",
                "artist": "Old",
                "communities": {"res_10": "C010"},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    G = nx.DiGraph()
    G.add_node("old", display_name="Old")
    G.add_node("fresh", display_name="Fresh")
    G.add_edge("fresh", "old", weight=1.0)
    export_communities_incremental(G, [10.0], tmp_path, prev)
    memb = load_artist_communities(tmp_path / "community_memberships.jsonl")
    assert memb["old"]["res_10"] == "C010"
    assert memb["fresh"]["res_10"] == "C010"
    comm_path = tmp_path / "communities_res_10.json"
    clist, res = load_communities(comm_path)
    assert res == 10.0
    assert len(clist) == 1
    assert clist[0]["id"] == "C010"
    assert set(clist[0]["artists"]) == {"Fresh", "Old"}
