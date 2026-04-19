"""Publish newest-review playlist candidates to the Deezer API (library code).

Used by the Streamlit Deezer playlist flow: create a new playlist or replace
the tracks of an existing owned playlist when the user-chosen name matches.
After (re)publishing, the playlist's ``public`` flag is set to match the
caller's request because Deezer creates playlists as private by default.
"""

from __future__ import annotations

import logging

from music_review.dashboard.newest_spotify_playlist import PlaylistCandidate
from music_review.integrations.deezer_client import (
    DeezerClient,
    DeezerPlaylist,
    DeezerToken,
    deezer_track_id_from_uri,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_NEUESTE_DEEZER_PLAYLIST_DESCRIPTION = (
    "Playlist aus aktuellen Album-Rezensionen von "
    "plattentests.de - passend zu Deinem persönlichen Musikgeschmack."
)


def _candidates_to_track_ids(candidates: list[PlaylistCandidate]) -> list[str]:
    """Translate ``deezer:track:{id}`` URIs to bare numeric Deezer track ids.

    Candidates whose URI is empty or does not look like a Deezer URI are
    skipped silently; the publisher only forwards numeric ids that Deezer
    will accept on the ``/playlist/{id}/tracks`` endpoint.
    """
    out: list[str] = []
    for cand in candidates:
        raw = cand.spotify_uri
        if not isinstance(raw, str) or not raw.strip():
            continue
        track_id = deezer_track_id_from_uri(raw)
        if track_id:
            out.append(track_id)
    return out


def publish_deezer_playlist_for_candidates(
    client: DeezerClient,
    token: DeezerToken,
    *,
    candidates: list[PlaylistCandidate],
    resolved_name: str,
    public: bool,
    description: str = DEFAULT_NEUESTE_DEEZER_PLAYLIST_DESCRIPTION,
) -> tuple[DeezerPlaylist, bool]:
    """Create or overwrite-by-name a Deezer playlist with ``candidates``.

    Returns ``(playlist, created)`` where ``created`` is ``True`` for a new
    playlist and ``False`` when an existing owned playlist was matched by
    name and its tracks were replaced.

    The ``description`` is currently not pushed to Deezer (the public REST
    API endpoint does not expose a stable description-update field for
    user playlists); the parameter is accepted for API symmetry with the
    Spotify publisher.
    """
    name = resolved_name.strip()
    if not name:
        msg = "Playlist title must be non-empty"
        raise ValueError(msg)
    _ = description  # Reserved for future symmetric use; see docstring.

    track_ids = _candidates_to_track_ids(candidates)
    existing_id = client.find_owned_playlist_id_by_display_name(
        display_name=name,
        token=token,
    )
    if existing_id is not None:
        LOGGER.info(
            "publish_deezer_playlist: replacing tracks on existing playlist "
            "id=%s n_tracks=%s",
            existing_id,
            len(track_ids),
        )
        client.replace_all_playlist_tracks(
            playlist_id=existing_id,
            track_ids=track_ids,
            token=token,
        )
        client.set_playlist_visibility(
            playlist_id=existing_id,
            public=public,
            token=token,
        )
        playlist = client.get_playlist(playlist_id=existing_id, token=token)
        return playlist, False

    LOGGER.info(
        "publish_deezer_playlist: creating new playlist name=%r public=%s n_tracks=%s",
        name,
        public,
        len(track_ids),
    )
    playlist = client.create_playlist(title=name, token=token)
    if track_ids:
        client.add_tracks_to_playlist(
            playlist_id=playlist.id,
            track_ids=track_ids,
            token=token,
        )
    client.set_playlist_visibility(
        playlist_id=playlist.id,
        public=public,
        token=token,
    )
    return playlist, True
