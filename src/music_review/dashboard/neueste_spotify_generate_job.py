"""Background-safe Spotify playlist generation for the newest-reviews flow.

Runs the slow Spotify search + publish steps so a Streamlit rerun can finish
quickly (avoids reverse-proxy upstream timeouts on long synchronous requests).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from music_review.dashboard.neueste_spotify_publish import (
    publish_playlist_for_candidates,
)
from music_review.dashboard.newest_spotify_playlist import (
    build_playlist_candidates,
    resolve_track_uri_strict,
)
from music_review.domain.models import Review
from music_review.integrations.spotify_client import SpotifyClient, SpotifyToken

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NeuesteSpotifyGenerateOutcome:
    """Result of :func:`run_neueste_spotify_publish_pipeline` for UI handling."""

    publish_succeeded: bool
    playlist_id: str
    external_url: str
    created: bool
    warn_partial_candidates: str | None
    error_no_candidates: bool
    error_value_message: str | None
    error_runtime_message: str | None
    show_runtime_403_caption: bool
    unexpected_error: str | None

    @classmethod
    def unexpected(cls, message: str) -> NeuesteSpotifyGenerateOutcome:
        """Build an outcome for an unexpected exception (non-Spotify API)."""
        return cls(
            publish_succeeded=False,
            playlist_id="",
            external_url="",
            created=False,
            warn_partial_candidates=None,
            error_no_candidates=False,
            error_value_message=None,
            error_runtime_message=None,
            show_runtime_403_caption=False,
            unexpected_error=message,
        )


def run_neueste_spotify_publish_pipeline(
    *,
    client: SpotifyClient,
    token: SpotifyToken,
    chosen_reviews: list[Review],
    alloc_weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    resolved_playlist_name: str,
    public: bool,
) -> NeuesteSpotifyGenerateOutcome:
    """Resolve tracks, build candidates, and publish to Spotify.

    Intended to run in a worker thread; do not call Streamlit APIs here.
    """
    warn_partial: str | None = None
    try:
        LOGGER.info(
            "neueste spotify job: start build_playlist_candidates "
            "n_albums=%s target_count=%s",
            len(chosen_reviews),
            target_count,
        )
        candidates = build_playlist_candidates(
            reviews=chosen_reviews,
            weights=alloc_weights,
            raw_scores=raw_scores,
            target_count=target_count,
            rng=rng,
            resolve_fn=lambda *, artist, track_title: resolve_track_uri_strict(
                client,
                token,
                artist=artist,
                track_title=track_title,
            ),
        )
        LOGGER.info(
            "neueste spotify job: finished n_candidates=%s (target was %s)",
            len(candidates),
            target_count,
        )
    except Exception as exc:
        LOGGER.exception("neueste spotify job: build_playlist_candidates failed")
        return NeuesteSpotifyGenerateOutcome.unexpected(repr(exc))

    if len(candidates) < target_count:
        warn_partial = (
            "Es konnten nicht genug eindeutige Spotify-Treffer gefunden werden. "
            f"Gefunden: {len(candidates)} von {target_count}. Die Playlist "
            "wird nur mit diesen Songs befüllt."
        )

    if not candidates:
        return NeuesteSpotifyGenerateOutcome(
            publish_succeeded=False,
            playlist_id="",
            external_url="",
            created=False,
            warn_partial_candidates=warn_partial,
            error_no_candidates=True,
            error_value_message=None,
            error_runtime_message=None,
            show_runtime_403_caption=False,
            unexpected_error=None,
        )

    try:
        playlist, created = publish_playlist_for_candidates(
            client,
            token,
            candidates=candidates,
            resolved_name=resolved_playlist_name,
            public=public,
        )
    except ValueError as exc:
        return NeuesteSpotifyGenerateOutcome(
            publish_succeeded=False,
            playlist_id="",
            external_url="",
            created=False,
            warn_partial_candidates=warn_partial,
            error_no_candidates=False,
            error_value_message=str(exc),
            error_runtime_message=None,
            show_runtime_403_caption=False,
            unexpected_error=None,
        )
    except RuntimeError as exc:
        detail = str(exc)
        show_403 = "403" in detail or "forbidden" in detail.casefold()
        return NeuesteSpotifyGenerateOutcome(
            publish_succeeded=False,
            playlist_id="",
            external_url="",
            created=False,
            warn_partial_candidates=warn_partial,
            error_no_candidates=False,
            error_value_message=None,
            error_runtime_message=detail,
            show_runtime_403_caption=show_403,
            unexpected_error=None,
        )
    except Exception as exc:
        LOGGER.exception("neueste spotify job: publish failed unexpectedly")
        return NeuesteSpotifyGenerateOutcome(
            publish_succeeded=False,
            playlist_id="",
            external_url="",
            created=False,
            warn_partial_candidates=warn_partial,
            error_no_candidates=False,
            error_value_message=None,
            error_runtime_message=None,
            show_runtime_403_caption=False,
            unexpected_error=repr(exc),
        )

    return NeuesteSpotifyGenerateOutcome(
        publish_succeeded=True,
        playlist_id=playlist.id,
        external_url=playlist.external_url or "",
        created=created,
        warn_partial_candidates=warn_partial,
        error_no_candidates=False,
        error_value_message=None,
        error_runtime_message=None,
        show_runtime_403_caption=False,
        unexpected_error=None,
    )
