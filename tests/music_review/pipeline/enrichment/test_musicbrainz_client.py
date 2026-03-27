"""Tests for musicbrainz_client helpers without real network calls."""

from __future__ import annotations

from music_review.pipeline.enrichment import musicbrainz_client as mb


def test_select_best_artist_prefers_highest_score() -> None:
    """Highest numeric score candidate is selected."""
    best = mb._select_best_artist(
        [
            {"id": "a", "score": "42"},
            {"id": "b", "score": "99"},
            {"id": "c", "score": "10"},
        ]
    )
    assert best is not None
    assert best["id"] == "b"


def test_extract_band_members_filters_direction_and_target_type() -> None:
    """Only backward artist member relations are used."""
    entity = {
        "relations": [
            {
                "type": "member of band",
                "target-type": "artist",
                "direction": "backward",
                "artist": {"name": "Member A"},
            },
            {
                "type": "member of band",
                "target-type": "artist",
                "direction": "forward",
                "artist": {"name": "Should Be Ignored"},
            },
            {
                "type": "other",
                "target-type": "artist",
                "direction": "backward",
                "artist": {"name": "Ignored Too"},
            },
        ]
    }
    assert mb._extract_band_members(entity) == ["Member A"]


def test_extract_tag_names_normalizes_values() -> None:
    """Tag names are lowercased and stripped."""
    tags = mb._extract_tag_names(
        {"tags": [{"name": " Indie Rock "}, {"name": "Post-Rock"}]}
    )
    assert tags == ["indie rock", "post-rock"]


def test_fetch_album_tags_happy_path(monkeypatch) -> None:
    """fetch_album_tags builds ExternalGenreInfo from mocked lookups."""
    monkeypatch.setattr(
        mb,
        "search_release_groups",
        lambda **_: [{"id": "rg1", "title": "T", "primary-type": "Album"}],
    )
    monkeypatch.setattr(
        mb,
        "_lookup_release_group_with_tags",
        lambda _mbid: {"tags": [{"name": "Indie Rock"}]},
    )
    info = mb.fetch_album_tags("Artist", "Album")
    assert info is not None
    assert info.mbid == "rg1"
    assert info.tags == ["indie rock"]


def test_fetch_artist_info_returns_none_when_no_candidates(monkeypatch) -> None:
    """No search results yields None."""
    monkeypatch.setattr(mb, "_search_artists", lambda **_: [])
    assert mb.fetch_artist_info("unknown") is None


def test_fetch_album_genres_maps_tags(monkeypatch) -> None:
    """fetch_album_genres maps external tags to canonical internal genres."""
    monkeypatch.setattr(
        mb,
        "fetch_album_tags",
        lambda **_: mb.ExternalGenreInfo(
            mbid="x",
            title="t",
            artist="a",
            tags=["hip hop", "metal", "unknown"],
        ),
    )
    genres = mb.fetch_album_genres("a", "b")
    assert "hip_hop" in genres
    assert "metal" in genres
