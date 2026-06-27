"""Tests for musicbrainz_client helpers without real network calls."""

from __future__ import annotations

import requests

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


def test_select_best_artist_prefers_exact_name_match() -> None:
    """An exact artist-name match wins over a higher-scored homonym."""
    best = mb._select_best_artist(
        [
            {"id": "wrong", "name": "Josh Ritter", "score": "100"},
            {"id": "right", "name": "Josh.", "score": "42"},
        ],
        preferred_name="Josh.",
    )
    assert best is not None
    assert best["id"] == "right"


def test_extract_artist_mbid_from_release_group_reads_credit() -> None:
    """Release-group search hits expose the credited artist MBID."""
    mbid = mb.extract_artist_mbid_from_release_group(
        {
            "artist-credit": [
                {
                    "name": "Josh.",
                    "artist": {
                        "id": "dd3f09d1-9cd3-42d6-b711-3b1ca52d5266",
                        "name": "Josh.",
                    },
                },
            ],
        },
    )
    assert mbid == "dd3f09d1-9cd3-42d6-b711-3b1ca52d5266"


def test_fetch_album_tags_happy_path(monkeypatch) -> None:
    """fetch_album_tags builds ExternalGenreInfo from mocked lookups."""
    monkeypatch.setattr(
        mb,
        "search_release_groups",
        lambda **_: [
            {
                "id": "rg1",
                "title": "T",
                "primary-type": "Album",
                "artist-credit": [
                    {
                        "name": "Artist",
                        "artist": {"id": "artist-1", "name": "Artist"},
                    },
                ],
            },
        ],
    )
    monkeypatch.setattr(
        mb,
        "_lookup_release_group_with_tags",
        lambda _mbid: {"tags": [{"name": "Indie Rock"}]},
    )
    info = mb.fetch_album_tags("Artist", "Album")
    assert info is not None
    assert info.mbid == "rg1"
    assert info.artist_mbid == "artist-1"
    assert info.tags == ["indie rock"]


def test_fetch_artist_info_returns_none_when_no_candidates(monkeypatch) -> None:
    """No search results yields None."""
    monkeypatch.setattr(mb, "_search_artists", lambda **_: ([], False))
    assert mb.fetch_artist_info("unknown") is None


def test_fetch_artist_info_returns_none_when_search_fails(monkeypatch) -> None:
    """Transient MusicBrainz failures yield None without a not-found log."""
    monkeypatch.setattr(mb, "_search_artists", lambda **_: ([], True))
    assert mb.fetch_artist_info("Sibylle Kefer") is None


def test_get_retries_transient_ssl_errors(monkeypatch) -> None:
    """Transient SSL failures are retried before surfacing an error."""
    calls = {"count": 0}

    class FakeSSLError(requests.exceptions.ConnectionError):
        """Test-only connection error standing in for an SSL failure."""

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise FakeSSLError("ssl eof")
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"artists": []}'
        return response

    monkeypatch.setattr(mb.requests, "get", fake_get)
    monkeypatch.setattr(mb, "_sleep_backoff", lambda _attempt: None)
    monkeypatch.setattr(mb, "_sleep_if_needed", lambda: None)

    payload = mb._get("/artist", {"query": "Sibylle Kefer", "fmt": "json", "limit": 5})

    assert calls["count"] == 3
    assert payload == {"artists": []}


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
