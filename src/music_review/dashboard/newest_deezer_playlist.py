"""Resolve track URIs from newest reviews against Deezer.

The candidate-building algorithm is provider-agnostic: the existing
:func:`music_review.dashboard.newest_spotify_playlist.build_playlist_candidates`
takes a callable ``resolve_fn`` and stores whatever URI string it returns on
the candidate's ``spotify_uri`` field. This module supplies the Deezer
implementation of that callable.

It mirrors :func:`...newest_spotify_playlist.resolve_track_uri_strict` but
uses :class:`~music_review.integrations.deezer_client.DeezerClient` and
returns Deezer track URIs in the form ``deezer:track:{numeric_id}``.

Logging uses ``music_review.dashboard.newest_deezer_playlist`` (English
messages). INFO: fallback variant matches; WARNING: no match after all
variants; DEBUG: each tried query and accepted/sole result.
"""

from __future__ import annotations

import logging

from music_review.dashboard.newest_spotify_playlist import (
    _artist_matches_review_vs_spotify,
    _log_str,
    _titles_match_review_vs_spotify,
    spotify_resolve_query_variants,
)
from music_review.integrations.deezer_client import (
    DeezerClient,
    DeezerToken,
    DeezerTrack,
    deezer_track_uri,
)

LOGGER = logging.getLogger(__name__)


def _pick_deezer_uri_from_search_results(
    results: list[DeezerTrack],
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Pick one Deezer URI from a search result page.

    A "plausible" hit matches both title and artist using the same
    matchers used for Spotify (umlaut folding, feat/remix stripping,
    suffix tolerance). When more than one row is plausible the **first**
    is kept. When no row is plausible but the API returned exactly one
    track, that track is accepted as a sole result.
    """
    plausible: list[DeezerTrack] = [
        r
        for r in results
        if _titles_match_review_vs_spotify(track_title, r.title)
        and _artist_matches_review_vs_spotify(artist, (r.artist,))
    ]
    if plausible:
        chosen = plausible[0]
        if len(plausible) > 1:
            LOGGER.info(
                "Deezer resolve: multiple matching tracks, using first n=%s "
                "first_id=%s",
                len(plausible),
                chosen.id,
            )
        LOGGER.debug(
            "Deezer resolve: accepted match track_id=%s title=%r",
            chosen.id,
            _log_str(chosen.title, max_len=80),
        )
        return deezer_track_uri(chosen.id)
    if len(results) == 1:
        only = results[0]
        LOGGER.debug(
            "Deezer resolve: accepted sole API result track_id=%s title=%r",
            only.id,
            _log_str(only.title, max_len=80),
        )
        return deezer_track_uri(only.id)
    LOGGER.debug(
        "Deezer resolve: no usable match in this result set "
        "n_results=%s n_plausible=%s artist=%r track=%r top_titles=%s",
        len(results),
        len(plausible),
        _log_str(artist),
        _log_str(track_title),
        [_log_str(r.title, max_len=40) for r in results[:5]],
    )
    return None


def resolve_track_uri_strict(
    client: DeezerClient,
    token: DeezerToken,
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Resolve a track to a Deezer URI via search with multiple query variants.

    Tries each query shape produced by
    :func:`...newest_spotify_playlist.spotify_resolve_query_variants` -- the
    same shapes work for Deezer because Deezer also accepts ``artist:"…"
    track:"…"`` queries and falls back gracefully to loose text searches.
    """
    queries = spotify_resolve_query_variants(artist, track_title)
    for variant_index, query in enumerate(queries):
        LOGGER.debug(
            "Deezer resolve: query variant=%s q=%r",
            variant_index,
            _log_str(query, max_len=220),
        )
        results = client.search_tracks(query=query, token=token, limit=10)
        if not results:
            continue
        picked = _pick_deezer_uri_from_search_results(
            results,
            artist=artist,
            track_title=track_title,
        )
        if picked:
            if variant_index > 0:
                LOGGER.info(
                    "Deezer resolve: match via fallback query variant_index=%s",
                    variant_index,
                )
            return picked
    LOGGER.warning(
        "Deezer resolve: no results after %s query variants artist=%r track=%r",
        len(queries),
        _log_str(artist),
        _log_str(track_title),
    )
    return None
