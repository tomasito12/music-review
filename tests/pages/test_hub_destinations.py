"""Tests for Hub destination registry."""

from __future__ import annotations

from pages.hub_destinations import HUB_DESTINATIONS, hub_destinations


def test_hub_destinations_returns_tuple_of_cards() -> None:
    dests = hub_destinations()
    assert dests == HUB_DESTINATIONS
    assert len(dests) >= 4
    for d in dests:
        assert d.title
        assert d.description
        assert d.page_path.startswith("pages/")
        assert d.page_path.endswith(".py")
