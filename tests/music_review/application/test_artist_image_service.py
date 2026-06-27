"""Tests for cached artist image lookups."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.application.artist_image_service import (
    ArtistImageService,
    is_negative_cache_fresh,
)


def test_is_negative_cache_fresh_respects_ttl() -> None:
    """Negative cache entries expire after the configured TTL."""
    fetched_at = (datetime.now(UTC) - timedelta(days=10)).replace(microsecond=0)
    record = ArtistImageRecord(
        artist_mbid="mbid-1",
        artist_name="Alpha",
        status="not_found",
        fetched_at=fetched_at.isoformat(),
        reason="no_wikidata_id",
    )

    assert is_negative_cache_fresh(record, ttl_days=30) is True
    assert is_negative_cache_fresh(record, ttl_days=5) is False


def test_lookup_returns_cached_ok_record_without_resolver(tmp_path: Path) -> None:
    """A cached ok record is returned without calling the resolver."""
    cache_path = tmp_path / "artist_images.jsonl"
    cached = ArtistImageRecord(
        artist_mbid="mbid-1",
        artist_name="Alpha",
        status="ok",
        fetched_at=utc_now_iso(),
        thumbnail_url="https://example.com/thumb.jpg",
        license="CC BY 4.0",
        attribution_text="Alpha by User, CC BY 4.0 via Wikimedia Commons",
        source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
    )
    from music_review.application.artist_image_store import upsert_artist_image

    upsert_artist_image(cache_path, cached)
    resolver = MagicMock()
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=tmp_path / "artist_images",
        negative_ttl_days=30,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "music_review.application.artist_image_service.resolve_artist_image",
            resolver,
        )
        record = service.lookup("mbid-1")

    assert record.status == "ok"
    assert record.thumbnail_url == "https://example.com/thumb.jpg"
    resolver.assert_not_called()


def test_lookup_returns_fresh_negative_cache_without_resolver(tmp_path: Path) -> None:
    """A fresh negative cache entry blocks another external lookup."""
    cache_path = tmp_path / "artist_images.jsonl"
    cached = ArtistImageRecord(
        artist_mbid="mbid-2",
        artist_name="Beta",
        status="not_found",
        fetched_at=utc_now_iso(),
        reason="no_commons_image",
    )
    from music_review.application.artist_image_store import upsert_artist_image

    upsert_artist_image(cache_path, cached)
    resolver = MagicMock()
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=tmp_path / "artist_images",
        negative_ttl_days=30,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "music_review.application.artist_image_service.resolve_artist_image",
            resolver,
        )
        record = service.lookup("mbid-2")

    assert record.status == "not_found"
    resolver.assert_not_called()


def test_lookup_resolves_and_persists_on_cache_miss(tmp_path: Path) -> None:
    """Cache misses call the resolver and persist the result."""
    cache_path = tmp_path / "artist_images.jsonl"
    resolved = ArtistImageRecord(
        artist_mbid="mbid-3",
        artist_name="Gamma",
        status="ok",
        fetched_at=utc_now_iso(),
        thumbnail_url="https://example.com/gamma.jpg",
        license="CC0",
        attribution_text="Gamma, CC0 via Wikimedia Commons",
        source_url="https://commons.wikimedia.org/wiki/File:Gamma.jpg",
    )
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=tmp_path / "artist_images",
        negative_ttl_days=30,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "music_review.application.artist_image_service.resolve_artist_image",
            lambda **kwargs: resolved,
        )
        first = service.lookup("mbid-3", artist_name="Gamma")
        second = service.lookup("mbid-3", artist_name="Gamma")

    assert first.status == "ok"
    assert second.thumbnail_url == "https://example.com/gamma.jpg"
    assert cache_path.is_file()


def test_lookup_re_resolves_expired_negative_cache(tmp_path: Path) -> None:
    """Expired negative cache entries trigger a fresh resolver call."""
    cache_path = tmp_path / "artist_images.jsonl"
    stale_fetched_at = (
        (datetime.now(UTC) - timedelta(days=40)).replace(microsecond=0).isoformat()
    )
    stale = ArtistImageRecord(
        artist_mbid="mbid-4",
        artist_name="Delta",
        status="not_found",
        fetched_at=stale_fetched_at,
        reason="no_wikidata_id",
    )
    from music_review.application.artist_image_store import upsert_artist_image

    upsert_artist_image(cache_path, stale)
    resolver = MagicMock(
        return_value=ArtistImageRecord(
            artist_mbid="mbid-4",
            artist_name="Delta",
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/delta.jpg",
            license="CC BY 2.0",
            attribution_text="Delta, CC BY 2.0 via Wikimedia Commons",
            source_url="https://commons.wikimedia.org/wiki/File:Delta.jpg",
        ),
    )
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=tmp_path / "artist_images",
        negative_ttl_days=30,
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "music_review.application.artist_image_service.resolve_artist_image",
            resolver,
        )
        record = service.lookup("mbid-4")

    assert record.status == "ok"
    resolver.assert_called_once()
