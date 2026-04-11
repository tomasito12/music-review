"""Tests for publishing newest-review candidates to Spotify."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.neueste_spotify_publish import (
    publish_playlist_for_candidates,
)
from music_review.dashboard.newest_spotify_playlist import PlaylistCandidate
from music_review.integrations.spotify_client import SpotifyPlaylist, SpotifyToken


def _candidate(uri: str = "spotify:track:ab") -> PlaylistCandidate:
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


def _token() -> SpotifyToken:
    return SpotifyToken(
        access_token="tok",
        token_type="Bearer",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        refresh_token="r",
        scope="playlist-modify-private",
    )


def test_publish_playlist_creates_when_no_name_match() -> None:
    client = MagicMock()
    client.find_owned_playlist_id_by_display_name.return_value = None
    client.create_playlist.return_value = SpotifyPlaylist(
        id="newpl",
        name="My Mix",
        uri="spotify:playlist:newpl",
        external_url="https://open.spotify.com/playlist/newpl",
    )

    pl, created = publish_playlist_for_candidates(
        client,
        _token(),
        candidates=[_candidate("spotify:track:a")],
        resolved_name="My Mix",
        public=False,
    )

    assert created is True
    assert pl.id == "newpl"
    client.create_playlist.assert_called_once()
    client.replace_all_playlist_tracks.assert_not_called()
    client.add_tracks_to_playlist.assert_called_once()


def test_publish_playlist_replaces_when_name_match() -> None:
    client = MagicMock()
    client.find_owned_playlist_id_by_display_name.return_value = "existing"
    client.get_playlist.return_value = SpotifyPlaylist(
        id="existing",
        name="My Mix",
        uri="spotify:playlist:existing",
        external_url="https://open.spotify.com/playlist/existing",
    )

    pl, created = publish_playlist_for_candidates(
        client,
        _token(),
        candidates=[_candidate("spotify:track:z")],
        resolved_name="My Mix",
        public=True,
    )

    assert created is False
    assert pl.id == "existing"
    client.replace_all_playlist_tracks.assert_called_once()
    client.patch_playlist_details.assert_called_once()
    client.create_playlist.assert_not_called()


def test_publish_playlist_rejects_empty_name() -> None:
    client = MagicMock()
    with pytest.raises(ValueError, match="non-empty"):
        publish_playlist_for_candidates(
            client,
            _token(),
            candidates=[_candidate()],
            resolved_name="   ",
            public=False,
        )
