"""Tests for publishing newest-review candidates to Deezer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.neueste_deezer_publish import (
    _candidates_to_track_ids,
    publish_deezer_playlist_for_candidates,
)
from music_review.dashboard.newest_spotify_playlist import PlaylistCandidate
from music_review.integrations.deezer_client import DeezerPlaylist, DeezerToken


def _candidate(uri: str = "deezer:track:42") -> PlaylistCandidate:
    return PlaylistCandidate(
        review_id=1,
        artist="Artist",
        album="Album",
        track_title="Track",
        source_kind="highlight",
        spotify_uri=uri,
        score_weight=1.0,
        raw_score=1.0,
        playlist_slot_quota=1,
        strat_ideal_slots=1.0,
        strat_floor_slots=1,
        strat_remainder_extra_slots=0,
    )


def _token() -> DeezerToken:
    return DeezerToken(
        access_token="tok",
        expires_in=0,
        obtained_at=datetime.now(tz=UTC),
    )


def test_candidates_to_track_ids_extracts_numeric_ids() -> None:
    """Deezer URIs are converted into bare numeric track ids."""
    out = _candidates_to_track_ids(
        [_candidate("deezer:track:111"), _candidate("deezer:track:222")],
    )
    assert out == ["111", "222"]


def test_candidates_to_track_ids_skips_non_deezer_uris() -> None:
    """Empty / non-Deezer URIs are skipped silently."""
    out = _candidates_to_track_ids(
        [
            _candidate("deezer:track:111"),
            _candidate(""),
            _candidate("spotify:track:abc"),
            _candidate("deezer:track:222"),
        ],
    )
    assert out == ["111", "222"]


def test_publish_deezer_playlist_creates_when_no_name_match() -> None:
    """Without a matching playlist, a new one is created and tracks are added."""
    client = MagicMock()
    client.find_owned_playlist_id_by_display_name.return_value = None
    client.create_playlist.return_value = DeezerPlaylist(
        id="newpl",
        title="My Mix",
        link="https://www.deezer.com/playlist/newpl",
    )

    pl, created = publish_deezer_playlist_for_candidates(
        client,
        _token(),
        candidates=[_candidate("deezer:track:a")],
        resolved_name="My Mix",
        public=False,
    )

    assert created is True
    assert pl.id == "newpl"
    client.create_playlist.assert_called_once()
    client.replace_all_playlist_tracks.assert_not_called()
    client.add_tracks_to_playlist.assert_called_once()
    client.set_playlist_visibility.assert_called_once()
    _, kwargs = client.set_playlist_visibility.call_args
    assert kwargs["public"] is False


def test_publish_deezer_playlist_replaces_when_name_match() -> None:
    """When an owned playlist matches the name, tracks are replaced in place."""
    client = MagicMock()
    client.find_owned_playlist_id_by_display_name.return_value = "existing"
    client.get_playlist.return_value = DeezerPlaylist(
        id="existing",
        title="My Mix",
        link="https://www.deezer.com/playlist/existing",
    )

    pl, created = publish_deezer_playlist_for_candidates(
        client,
        _token(),
        candidates=[_candidate("deezer:track:z")],
        resolved_name="My Mix",
        public=True,
    )

    assert created is False
    assert pl.id == "existing"
    client.replace_all_playlist_tracks.assert_called_once()
    client.set_playlist_visibility.assert_called_once()
    _, kwargs = client.set_playlist_visibility.call_args
    assert kwargs["public"] is True
    client.create_playlist.assert_not_called()


def test_publish_deezer_playlist_rejects_empty_name() -> None:
    """Whitespace-only names raise ``ValueError`` before any API call runs."""
    client = MagicMock()
    with pytest.raises(ValueError, match="non-empty"):
        publish_deezer_playlist_for_candidates(
            client,
            _token(),
            candidates=[_candidate()],
            resolved_name="   ",
            public=False,
        )


def test_publish_deezer_playlist_creates_with_no_tracks_when_unresolved() -> None:
    """When all candidates are non-Deezer URIs, the playlist is still created."""
    client = MagicMock()
    client.find_owned_playlist_id_by_display_name.return_value = None
    client.create_playlist.return_value = DeezerPlaylist(
        id="empty",
        title="Empty Mix",
        link="https://www.deezer.com/playlist/empty",
    )

    pl, created = publish_deezer_playlist_for_candidates(
        client,
        _token(),
        candidates=[_candidate("spotify:track:nope")],
        resolved_name="Empty Mix",
        public=False,
    )

    assert created is True
    assert pl.id == "empty"
    client.add_tracks_to_playlist.assert_not_called()
    client.set_playlist_visibility.assert_called_once()
