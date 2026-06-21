"""Tests for CLI default paths aligned with data_access.paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.data_access.paths import (
    DATA_ARTIST_REFERENCE_GRAPH,
    DATA_METADATA,
    DATA_REVIEWS,
    artist_reference_graph_path,
    reviews_path,
)
from music_review.pipeline.enrichment.artist_genres import (
    parse_args as artist_genres_parse_args,
)
from music_review.pipeline.retrieval.reference_graph_cli import _build_parser


def test_reference_graph_cli_defaults_match_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(tmp_path))
    parser = _build_parser()
    defaults = parser.parse_args([])
    assert defaults.reviews == reviews_path()
    assert defaults.output == artist_reference_graph_path()


def test_artist_genres_cli_default_metadata_is_data_metadata() -> None:
    args = artist_genres_parse_args([])
    assert args.metadata == Path(DATA_METADATA)


def test_fetch_metadata_cli_default_output_is_data_metadata() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews", type=Path, default=Path(DATA_REVIEWS))
    parser.add_argument("--output", type=Path, default=Path(DATA_METADATA))
    args = parser.parse_args([])
    assert args.output == Path(DATA_METADATA)


def test_path_constants_use_data_directory() -> None:
    assert reviews_path().name == Path(DATA_REVIEWS).name
    assert artist_reference_graph_path().name == Path(DATA_ARTIST_REFERENCE_GRAPH).name
