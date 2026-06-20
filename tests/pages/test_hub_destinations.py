"""Tests for Hub destination registry."""

from __future__ import annotations

from pages.hub_destinations import HUB_DESTINATIONS, hub_destinations


def test_hub_destinations_returns_tuple_of_cards() -> None:
    dests = hub_destinations()
    assert dests == HUB_DESTINATIONS
    assert len(dests) >= 5
    for d in dests:
        assert d.title
        assert d.description
        assert d.page_path.startswith("pages/")
        assert d.page_path.endswith(".py")


def test_hub_has_playlist_card_without_streaming_connection() -> None:
    """Playlist suggestions are a hub card; streaming OAuth setup was removed."""
    dests = hub_destinations()
    paths = [d.page_path for d in dests]
    assert "pages/9_Playlist_Erzeugen.py" in paths
    assert "pages/3_Streaming_Verbindungen.py" not in paths
    titles = {d.page_path: d.title for d in dests}
    assert titles["pages/9_Playlist_Erzeugen.py"] == "Playlist erzeugen"


def test_playlist_card_description_mentions_both_playlist_sources() -> None:
    """The Playlist hub card should advertise both playlist generation modes."""
    dests = hub_destinations()
    by_path = {d.page_path: d for d in dests}
    desc = by_path["pages/9_Playlist_Erzeugen.py"].description
    assert "neuesten Rezensionen" in desc
    assert "Archiv" in desc


def test_playlist_card_description_is_provider_agnostic() -> None:
    """The hub card no longer references Spotify or Deezer."""
    dests = hub_destinations()
    by_path = {d.page_path: d for d in dests}
    desc = by_path["pages/9_Playlist_Erzeugen.py"].description
    assert "Spotify" not in desc
    assert "Deezer" not in desc
    assert "Vorschlagsliste" in desc
