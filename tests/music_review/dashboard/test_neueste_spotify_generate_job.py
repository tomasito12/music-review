from __future__ import annotations

import random
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.neueste_spotify_generate_job import (
    NeuesteSpotifyGenerateOutcome,
    run_neueste_spotify_publish_pipeline,
)
from music_review.domain.models import Review, Track
from music_review.integrations.spotify_client import SpotifyPlaylist, SpotifyToken


def _review_with_tracks(review_id: int = 1) -> Review:
    tracks = [
        Track(number=1, title="Song A"),
        Track(number=2, title="Song B"),
    ]
    return Review(
        id=review_id,
        url=f"https://example.org/{review_id}",
        artist="Test Artist",
        album="Test Album",
        text="text",
        tracklist=tracks,
    )


def test_outcome_unexpected_factory() -> None:
    out = NeuesteSpotifyGenerateOutcome.unexpected("boom")
    assert out.publish_succeeded is False
    assert out.unexpected_error == "boom"


def test_pipeline_returns_no_candidates_when_build_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "music_review.dashboard.neueste_spotify_generate_job.build_playlist_candidates",
        lambda **_: [],
    )
    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    review = _review_with_tracks()
    out = run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[review],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=10,
        rng=random.Random(0),
        resolved_playlist_name="Plattenradar",
        public=False,
    )
    assert out.error_no_candidates is True
    assert out.publish_succeeded is False
    client.create_playlist.assert_not_called()


def test_pipeline_forwards_selection_strategy_to_build_playlist_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Archive mode must propagate ``selection_strategy='weighted_sample'`` to
    :func:`build_playlist_candidates`; otherwise the new sampling does nothing.
    """
    captured: dict[str, object] = {}

    def _spy(**kwargs: object) -> list[object]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "music_review.dashboard.neueste_spotify_generate_job.build_playlist_candidates",
        _spy,
    )
    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=5,
        rng=random.Random(0),
        resolved_playlist_name="Archiv",
        public=False,
        selection_strategy="weighted_sample",
    )
    assert captured.get("selection_strategy") == "weighted_sample"


def test_pipeline_defaults_selection_strategy_to_stratified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing callers without the new argument must keep the legacy behaviour."""
    captured: dict[str, object] = {}

    def _spy(**kwargs: object) -> list[object]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "music_review.dashboard.neueste_spotify_generate_job.build_playlist_candidates",
        _spy,
    )
    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=5,
        rng=random.Random(0),
        resolved_playlist_name="Neueste",
        public=False,
    )
    assert captured.get("selection_strategy") == "stratified"


def test_pipeline_value_error_from_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from music_review.dashboard import neueste_spotify_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "spotify:track:abc"

    monkeypatch.setattr(
        mod,
        "build_playlist_candidates",
        lambda **_: [fake_candidate],
    )

    def _raise_value_error(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[SpotifyPlaylist, bool]:
        raise ValueError("empty name")

    monkeypatch.setattr(
        mod,
        "publish_playlist_for_candidates",
        _raise_value_error,
    )

    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    review = _review_with_tracks()
    out = run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[review],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=False,
    )
    assert out.error_value_message == "empty name"
    assert out.publish_succeeded is False


def test_pipeline_runtime_error_sets_403_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from music_review.dashboard import neueste_spotify_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "spotify:track:abc"

    monkeypatch.setattr(
        mod,
        "build_playlist_candidates",
        lambda **_: [fake_candidate],
    )

    def _raise_runtime(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[SpotifyPlaylist, bool]:
        raise RuntimeError("Spotify API error 403 for GET /me: forbidden")

    monkeypatch.setattr(
        mod,
        "publish_playlist_for_candidates",
        _raise_runtime,
    )

    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    review = _review_with_tracks()
    out = run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[review],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=False,
    )
    assert out.show_runtime_403_caption is True
    assert out.error_runtime_message is not None


def test_pipeline_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from music_review.dashboard import neueste_spotify_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "spotify:track:abc"

    monkeypatch.setattr(
        mod,
        "build_playlist_candidates",
        lambda **_: [fake_candidate],
    )

    playlist = SpotifyPlaylist(
        id="pl1",
        name="X",
        uri="spotify:playlist:pl1",
        external_url="https://open.spotify.com/playlist/pl1",
    )

    monkeypatch.setattr(
        mod,
        "publish_playlist_for_candidates",
        lambda *_a, **_k: (playlist, True),
    )

    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    review = _review_with_tracks()
    out = run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[review],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=5,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=True,
    )
    assert out.publish_succeeded is True
    assert out.playlist_id == "pl1"
    assert out.created is True
    assert out.external_url.startswith("https://")


def test_pipeline_wraps_build_exception_as_unexpected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from music_review.dashboard import neueste_spotify_generate_job as mod

    def _boom(**_: object) -> list[MagicMock]:
        raise OSError("disk full")

    monkeypatch.setattr(mod, "build_playlist_candidates", _boom)
    client = MagicMock()
    token = MagicMock(spec=SpotifyToken)
    review = _review_with_tracks()
    out = run_neueste_spotify_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[review],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=False,
    )
    assert out.unexpected_error is not None
    assert "disk full" in out.unexpected_error
