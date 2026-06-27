"""Tests for artist thumbnail download helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import requests

from music_review.application.artist_image_download import (
    download_thumbnail,
    local_image_file_path,
    local_image_relative_path,
)


def test_local_image_relative_path_uses_mbid_filename() -> None:
    """Local cache paths are stable per artist MBID."""
    assert local_image_relative_path("mbid-1") == "artist_images/mbid-1.jpg"


def test_download_thumbnail_writes_image_bytes(tmp_path: Path, monkeypatch) -> None:
    """A successful HTTP response is stored as a local JPG file."""
    dest_path = local_image_file_path(tmp_path, "mbid-1")

    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: SimpleNamespace(
            content=b"fake-image",
            headers={"Content-Type": "image/jpeg"},
            raise_for_status=lambda: None,
        ),
    )

    assert download_thumbnail("https://example.com/thumb.jpg", dest_path) is True
    assert dest_path.read_bytes() == b"fake-image"


def test_download_thumbnail_rejects_non_image_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Non-image responses are rejected."""
    dest_path = local_image_file_path(tmp_path, "mbid-2")

    monkeypatch.setattr(
        requests,
        "get",
        lambda *_args, **_kwargs: SimpleNamespace(
            content=b"not-an-image",
            headers={"Content-Type": "text/html"},
            raise_for_status=lambda: None,
        ),
    )

    assert download_thumbnail("https://example.com/page.html", dest_path) is False
    assert not dest_path.exists()
