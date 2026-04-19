"""Background-safe Deezer playlist generation for the newest-reviews flow.

Mirrors :mod:`neueste_spotify_generate_job`: runs the slow Deezer search and
publish steps so a Streamlit rerun can finish quickly (avoids reverse-proxy
upstream timeouts on long synchronous requests).
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from music_review.dashboard.neueste_deezer_publish import (
    publish_deezer_playlist_for_candidates,
)
from music_review.dashboard.newest_spotify_playlist import (
    SelectionStrategy,
    build_playlist_candidates,
)
from music_review.domain.models import Review
from music_review.integrations.deezer_client import DeezerClient, DeezerToken
from music_review.integrations.streaming_catalog_cache import (
    deezer_resolve_with_streaming_catalog_cache,
    load_streaming_catalog_cache_from_env,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class NeuesteDeezerGenerateOutcome:
    """Result of :func:`run_neueste_deezer_publish_pipeline` for UI handling."""

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
    def unexpected(cls, message: str) -> NeuesteDeezerGenerateOutcome:
        """Build an outcome for an unexpected exception (non-Deezer API)."""
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


def run_neueste_deezer_publish_pipeline(
    *,
    client: DeezerClient,
    token: DeezerToken,
    chosen_reviews: list[Review],
    alloc_weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    resolved_playlist_name: str,
    public: bool,
    selection_strategy: SelectionStrategy = "stratified",
) -> NeuesteDeezerGenerateOutcome:
    """Resolve tracks, build candidates, and publish to Deezer.

    ``selection_strategy`` is forwarded to :func:`build_playlist_candidates`.
    Use ``"weighted_sample"`` for archive-style playlists where every
    qualifying album should have a real, score-weighted chance.

    Intended to run in a worker thread; do not call Streamlit APIs here.
    """
    warn_partial: str | None = None
    try:
        LOGGER.info(
            "neueste deezer job: start build_playlist_candidates "
            "n_albums=%s target_count=%s strategy=%s",
            len(chosen_reviews),
            target_count,
            selection_strategy,
        )
        catalog_cache = load_streaming_catalog_cache_from_env()

        def _resolve_tracks(*, artist: str, track_title: str) -> str | None:
            return deezer_resolve_with_streaming_catalog_cache(
                catalog_cache,
                client,
                token,
                artist=artist,
                track_title=track_title,
            )

        candidates = build_playlist_candidates(
            reviews=chosen_reviews,
            weights=alloc_weights,
            raw_scores=raw_scores,
            target_count=target_count,
            rng=rng,
            resolve_fn=_resolve_tracks,
            selection_strategy=selection_strategy,
        )
        LOGGER.info(
            "neueste deezer job: finished n_candidates=%s (target was %s)",
            len(candidates),
            target_count,
        )
    except Exception as exc:
        LOGGER.exception("neueste deezer job: build_playlist_candidates failed")
        return NeuesteDeezerGenerateOutcome.unexpected(repr(exc))

    if len(candidates) < target_count:
        warn_partial = (
            "Es konnten nicht genug eindeutige Deezer-Treffer gefunden werden. "
            f"Gefunden: {len(candidates)} von {target_count}. Die Playlist "
            "wird nur mit diesen Songs befüllt."
        )

    if not candidates:
        return NeuesteDeezerGenerateOutcome(
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
        playlist, created = publish_deezer_playlist_for_candidates(
            client,
            token,
            candidates=candidates,
            resolved_name=resolved_playlist_name,
            public=public,
        )
    except ValueError as exc:
        return NeuesteDeezerGenerateOutcome(
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
        return NeuesteDeezerGenerateOutcome(
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
        LOGGER.exception("neueste deezer job: publish failed unexpectedly")
        return NeuesteDeezerGenerateOutcome(
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

    return NeuesteDeezerGenerateOutcome(
        publish_succeeded=True,
        playlist_id=playlist.id,
        external_url=playlist.link or "",
        created=created,
        warn_partial_candidates=warn_partial,
        error_no_candidates=False,
        error_value_message=None,
        error_runtime_message=None,
        show_runtime_403_caption=False,
        unexpected_error=None,
    )
