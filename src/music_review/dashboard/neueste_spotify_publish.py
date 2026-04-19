"""Publish newest-review playlist candidates to the Spotify Web API (library code).

Used by the Streamlit Spotify page: create a new playlist or replace tracks on an
existing owned playlist when the user-chosen name matches (see Spotify client).
"""

from __future__ import annotations

import logging

from music_review.dashboard.newest_spotify_playlist import PlaylistCandidate
from music_review.integrations.spotify_client import (
    SpotifyClient,
    SpotifyPlaylist,
    SpotifyToken,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_NEUESTE_PLAYLIST_DESCRIPTION = (
    "Playlist aus aktuellen Album-Rezensionen von "
    "plattentests.de - passend zu Deinem persönlichen Musikgeschmack."
)


def publish_playlist_for_candidates(
    client: SpotifyClient,
    token: SpotifyToken,
    *,
    candidates: list[PlaylistCandidate],
    resolved_name: str,
    public: bool,
    description: str = DEFAULT_NEUESTE_PLAYLIST_DESCRIPTION,
) -> tuple[SpotifyPlaylist, bool]:
    """Create or overwrite-by-name a playlist and set tracks from ``candidates``.

    Returns ``(playlist, created)`` where ``created`` is ``True`` for a new
    playlist and ``False`` when an existing owned playlist was matched by name
    and its tracks were replaced.
    """
    name = resolved_name.strip()
    if not name:
        msg = "Playlist name must be non-empty"
        raise ValueError(msg)

    uris = [c.spotify_uri for c in candidates]
    existing_id = client.find_owned_playlist_id_by_display_name(
        display_name=name,
        token=token,
    )
    if existing_id is not None:
        LOGGER.info(
            "publish_playlist: replacing tracks on existing playlist id=%s n_tracks=%s",
            existing_id,
            len(uris),
        )
        client.replace_all_playlist_tracks(
            playlist_id=existing_id,
            track_uris=uris,
            token=token,
        )
        client.patch_playlist_details(
            playlist_id=existing_id,
            token=token,
            public=public,
        )
        playlist = client.get_playlist(playlist_id=existing_id, token=token)
        return playlist, False

    LOGGER.info(
        "publish_playlist: creating new playlist name=%r public=%s n_tracks=%s",
        name,
        public,
        len(uris),
    )
    playlist = client.create_playlist(
        name=name,
        description=description,
        public=public,
        token=token,
    )
    for idx in range(0, len(uris), 100):
        client.add_tracks_to_playlist(
            playlist_id=playlist.id,
            track_uris=uris[idx : idx + 100],
            token=token,
        )
    return playlist, True
