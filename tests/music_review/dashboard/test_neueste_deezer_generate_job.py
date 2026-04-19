"""Tests for the Deezer playlist generation pipeline / outcome dataclass."""

from __future__ import annotations

import random
from unittest.mock import MagicMock

import pytest

from music_review.dashboard.neueste_deezer_generate_job import (
    NeuesteDeezerGenerateOutcome,
    run_neueste_deezer_publish_pipeline,
)
from music_review.domain.models import Review, Track
from music_review.integrations.deezer_client import DeezerPlaylist, DeezerToken


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


def test_outcome_unexpected_factory_marks_failure() -> None:
    """The convenience factory builds a clearly-failing outcome."""
    out = NeuesteDeezerGenerateOutcome.unexpected("boom")
    assert out.publish_succeeded is False
    assert out.unexpected_error == "boom"


def test_pipeline_returns_no_candidates_when_build_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If candidate building yields nothing, the pipeline never publishes."""
    monkeypatch.setattr(
        "music_review.dashboard.neueste_deezer_generate_job.build_playlist_candidates",
        lambda **_: [],
    )
    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
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
    """Archive mode must propagate ``selection_strategy='weighted_sample'``."""
    captured: dict[str, object] = {}

    def _spy(**kwargs: object) -> list[object]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "music_review.dashboard.neueste_deezer_generate_job.build_playlist_candidates",
        _spy,
    )
    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    run_neueste_deezer_publish_pipeline(
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
    """Existing callers without the new argument get the legacy stratified flow."""
    captured: dict[str, object] = {}

    def _spy(**kwargs: object) -> list[object]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        "music_review.dashboard.neueste_deezer_generate_job.build_playlist_candidates",
        _spy,
    )
    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    run_neueste_deezer_publish_pipeline(
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


def test_pipeline_value_error_from_publish(monkeypatch: pytest.MonkeyPatch) -> None:
    """``ValueError`` from the publisher is mapped to ``error_value_message``."""
    from music_review.dashboard import neueste_deezer_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "deezer:track:abc"

    monkeypatch.setattr(mod, "build_playlist_candidates", lambda **_: [fake_candidate])

    def _raise_value_error(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[DeezerPlaylist, bool]:
        raise ValueError("empty name")

    monkeypatch.setattr(
        mod,
        "publish_deezer_playlist_for_candidates",
        _raise_value_error,
    )

    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
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
    """A 403-style ``RuntimeError`` raises the dedicated UI caption flag."""
    from music_review.dashboard import neueste_deezer_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "deezer:track:abc"

    monkeypatch.setattr(mod, "build_playlist_candidates", lambda **_: [fake_candidate])

    def _raise_runtime(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[DeezerPlaylist, bool]:
        raise RuntimeError("Deezer API error 403 for POST /playlist: forbidden")

    monkeypatch.setattr(mod, "publish_deezer_playlist_for_candidates", _raise_runtime)

    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=False,
    )
    assert out.show_runtime_403_caption is True
    assert out.error_runtime_message is not None


def test_pipeline_success_returns_playlist_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful publish populates id and external URL on the outcome."""
    from music_review.dashboard import neueste_deezer_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "deezer:track:abc"

    monkeypatch.setattr(mod, "build_playlist_candidates", lambda **_: [fake_candidate])

    playlist = DeezerPlaylist(
        id="pl1",
        title="X",
        link="https://www.deezer.com/playlist/pl1",
    )

    monkeypatch.setattr(
        mod,
        "publish_deezer_playlist_for_candidates",
        lambda *_a, **_k: (playlist, True),
    )

    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
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
    """Unexpected exceptions during candidate build become ``unexpected_error``."""
    from music_review.dashboard import neueste_deezer_generate_job as mod

    def _boom(**_: object) -> list[MagicMock]:
        raise OSError("disk full")

    monkeypatch.setattr(mod, "build_playlist_candidates", _boom)
    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=1,
        rng=random.Random(0),
        resolved_playlist_name="X",
        public=False,
    )
    assert out.unexpected_error is not None
    assert "disk full" in out.unexpected_error


def test_pipeline_partial_warning_message_when_below_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If fewer candidates than target are resolved, a German warning appears."""
    from music_review.dashboard import neueste_deezer_generate_job as mod

    fake_candidate = MagicMock()
    fake_candidate.spotify_uri = "deezer:track:abc"

    monkeypatch.setattr(mod, "build_playlist_candidates", lambda **_: [fake_candidate])

    playlist = DeezerPlaylist(
        id="pl9",
        title="Mix",
        link="https://www.deezer.com/playlist/pl9",
    )
    monkeypatch.setattr(
        mod,
        "publish_deezer_playlist_for_candidates",
        lambda *_a, **_k: (playlist, False),
    )

    client = MagicMock()
    token = MagicMock(spec=DeezerToken)
    out = run_neueste_deezer_publish_pipeline(
        client=client,
        token=token,
        chosen_reviews=[_review_with_tracks()],
        alloc_weights=[1.0],
        raw_scores=[1.0],
        target_count=5,
        rng=random.Random(0),
        resolved_playlist_name="Mix",
        public=False,
    )
    assert out.publish_succeeded is True
    assert out.warn_partial_candidates is not None
    assert "Deezer-Treffer" in out.warn_partial_candidates
