"""Tests for the Deezer track resolver used by the playlist pipeline."""

from __future__ import annotations

from typing import Any

from music_review.dashboard.newest_deezer_playlist import (
    _pick_deezer_uri_from_search_results,
    resolve_track_uri_strict,
)
from music_review.integrations.deezer_client import DeezerToken, DeezerTrack


def _track(track_id: str, title: str, artist: str) -> DeezerTrack:
    """Construct a minimal :class:`DeezerTrack` for testing."""
    return DeezerTrack(id=track_id, title=title, artist=artist, album=None, link=None)


class _FakeDeezerClient:
    """Minimal Deezer client stand-in that returns canned search results."""

    def __init__(
        self,
        results_by_query: dict[str, list[DeezerTrack]] | None = None,
    ) -> None:
        self._results_by_query = results_by_query or {}
        self.queries: list[str] = []

    def search_tracks(
        self,
        *,
        query: str,
        token: DeezerToken,
        limit: int = 10,
    ) -> list[DeezerTrack]:
        self.queries.append(query)
        return list(self._results_by_query.get(query, []))


def _token() -> DeezerToken:
    from datetime import UTC, datetime

    return DeezerToken(
        access_token="tok",
        expires_in=0,
        obtained_at=datetime.now(tz=UTC),
    )


def test_pick_deezer_uri_returns_first_plausible_match() -> None:
    """When several rows match title and artist, the first row wins."""
    rows = [
        _track("1", "The Weight", "The Band"),
        _track("2", "The Weight", "The Band"),
    ]
    uri = _pick_deezer_uri_from_search_results(
        rows, artist="The Band", track_title="The Weight"
    )
    assert uri == "deezer:track:1"


def test_pick_deezer_uri_returns_none_when_nothing_matches() -> None:
    """No plausible row and >1 results -> no URI is returned."""
    rows = [
        _track("1", "Different Song", "Different Artist"),
        _track("2", "Another Track", "Other Artist"),
    ]
    uri = _pick_deezer_uri_from_search_results(
        rows, artist="The Band", track_title="The Weight"
    )
    assert uri is None


def test_pick_deezer_uri_accepts_sole_result_even_if_not_strict_match() -> None:
    """A single API row is accepted even if title/artist normalize differently."""
    rows = [_track("9", "Weight", "Band")]
    uri = _pick_deezer_uri_from_search_results(
        rows, artist="The Band", track_title="The Weight"
    )
    assert uri == "deezer:track:9"


def test_pick_deezer_uri_empty_results_is_none() -> None:
    """Empty search response yields None."""
    assert _pick_deezer_uri_from_search_results([], artist="A", track_title="T") is None


def test_resolve_track_uri_strict_returns_first_query_hit() -> None:
    """The first matching query returns its URI without trying further variants."""
    primary_query = 'artist:"The Band" track:"The Weight"'
    client: Any = _FakeDeezerClient(
        results_by_query={
            primary_query: [_track("11", "The Weight", "The Band")],
        },
    )
    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="The Band",
        track_title="The Weight",
    )
    assert uri == "deezer:track:11"
    assert client.queries == [primary_query]


def test_resolve_track_uri_strict_falls_back_to_loose_query() -> None:
    """When quoted-field queries return nothing, loose text queries are tried."""
    loose_query = "The Band The Weight"
    client: Any = _FakeDeezerClient(
        results_by_query={
            loose_query: [_track("22", "The Weight", "The Band")],
        },
    )
    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="The Band",
        track_title="The Weight",
    )
    assert uri == "deezer:track:22"
    assert loose_query in client.queries
    assert client.queries.index(loose_query) > 0


def test_resolve_track_uri_strict_returns_none_when_all_queries_empty() -> None:
    """If no query yields results, the resolver returns None."""
    client: Any = _FakeDeezerClient(results_by_query={})
    uri = resolve_track_uri_strict(
        client,
        _token(),
        artist="Unknown",
        track_title="Nothing",
    )
    assert uri is None
    assert client.queries  # at least one variant was tried
