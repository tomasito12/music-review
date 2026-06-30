"""Tests for taste-community map layout generation."""

from __future__ import annotations

from music_review.application.community_map_layout import build_community_map_layout


def test_build_community_map_layout_uses_circular_fallback_without_graph() -> None:
    """Communities without graph edges still receive stable normalized positions."""
    communities = [
        {"id": "C001", "size": 10},
        {"id": "C002", "size": 20},
        {"id": "C003", "size": 5},
    ]

    nodes = build_community_map_layout(
        communities=communities,
        memberships={},
        graph_path="/path/does/not/exist.graphml",
    )

    assert len(nodes) == 3
    assert {node.id for node in nodes} == {"C001", "C002", "C003"}
    for node in nodes:
        assert 0.0 <= node.x <= 1.0
        assert 0.0 <= node.y <= 1.0
        assert node.neighbors == ()


def test_build_community_map_layout_returns_neighbors_from_cross_edges() -> None:
    """Cross-community reference edges define neighbor ordering."""
    communities = [
        {"id": "C001", "size": 1},
        {"id": "C002", "size": 1},
        {"id": "C003", "size": 1},
    ]
    memberships = {
        "alpha": {"res_10": "C001"},
        "beta": {"res_10": "C002"},
        "gamma": {"res_10": "C003"},
    }

    class _FakeGraph:
        def edges(self, data: bool = False):
            yield ("alpha", "beta", {"weight": 2.0})
            yield ("beta", "gamma", {"weight": 1.0})

    def _fake_load_graph(_path: str) -> _FakeGraph:
        return _FakeGraph()

    import music_review.application.community_map_layout as layout_module

    original_loader = layout_module.load_graph
    layout_module.load_graph = _fake_load_graph
    try:
        nodes = build_community_map_layout(
            communities=communities,
            memberships=memberships,
            graph_path="fake.graphml",
        )
    finally:
        layout_module.load_graph = original_loader

    by_id = {node.id: node for node in nodes}
    assert by_id["C002"].neighbors[0] == "C001"
    assert "C003" in by_id["C002"].neighbors


def test_build_community_map_layout_returns_empty_for_no_communities() -> None:
    """An empty community list yields an empty layout."""
    assert build_community_map_layout(communities=[]) == ()
