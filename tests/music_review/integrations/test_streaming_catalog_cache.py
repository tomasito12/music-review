"""Tests for deployment-wide streaming catalog SQLite cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from music_review.integrations import streaming_catalog_cache as scc_mod
from music_review.integrations.streaming_catalog_cache import (
    PROVIDER_SPOTIFY,
    StreamingCatalogCache,
    default_streaming_catalog_cache_path,
    load_streaming_catalog_cache_from_env,
    resolve_streaming_catalog_cache_path,
    spotify_resolve_with_streaming_catalog_cache,
    streaming_catalog_cache_enabled_from_env,
)


def test_streaming_catalog_cache_put_get_round_trip(tmp_path: Path) -> None:
    """Store and read back a URI for one provider and lookup key."""
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=True)
    assert cache.get("deezer", "a::b") is None
    cache.put("deezer", "a::b", "deezer:track:1")
    assert cache.get("deezer", "a::b") == "deezer:track:1"


def test_streaming_catalog_cache_same_key_different_providers(tmp_path: Path) -> None:
    """Two providers can store different URIs for the same logical lookup key."""
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=True)
    key = "artist::song"
    cache.put(PROVIDER_SPOTIFY, key, "spotify:track:aa")
    cache.put("deezer", key, "deezer:track:bb")
    assert cache.get(PROVIDER_SPOTIFY, key) == "spotify:track:aa"
    assert cache.get("deezer", key) == "deezer:track:bb"


def test_streaming_catalog_cache_put_overwrites_uri(tmp_path: Path) -> None:
    """Second put for the same (provider, key) replaces the stored URI."""
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=True)
    cache.put(PROVIDER_SPOTIFY, "k", "spotify:track:old")
    cache.put(PROVIDER_SPOTIFY, "k", "spotify:track:new")
    assert cache.get(PROVIDER_SPOTIFY, "k") == "spotify:track:new"


def test_streaming_catalog_cache_disabled_skips_storage(tmp_path: Path) -> None:
    """When disabled, get always returns None and put does not persist."""
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=False)
    assert cache.enabled is False
    cache.put(PROVIDER_SPOTIFY, "k", "spotify:track:x")
    assert cache.get(PROVIDER_SPOTIFY, "k") is None
    assert not db.exists()


def test_streaming_catalog_cache_empty_provider_or_key_returns_none(
    tmp_path: Path,
) -> None:
    """Whitespace-only provider or lookup key yields no read/write."""
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=True)
    cache.put("  ", "k", "spotify:track:x")
    cache.put(PROVIDER_SPOTIFY, "   ", "spotify:track:x")
    assert cache.get(" ", "k") is None
    assert cache.get(PROVIDER_SPOTIFY, " ") is None


def test_spotify_resolve_with_cache_calls_strict_only_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second resolve for the same artist/title reads SQLite, not strict resolver."""
    calls = {"n": 0}

    def fake_strict(
        _client: object,
        _token: object,
        *,
        artist: str,
        track_title: str,
    ) -> str:
        calls["n"] += 1
        assert artist == "The Band"
        assert track_title == "The Weight"
        return "spotify:track:cachedtest"

    monkeypatch.setattr(scc_mod, "resolve_track_uri_strict", fake_strict)
    db = tmp_path / "c.sqlite"
    cache = StreamingCatalogCache(db, enabled=True)
    client = MagicMock()
    token = MagicMock()
    uri1 = spotify_resolve_with_streaming_catalog_cache(
        cache,
        client,
        token,
        artist="The Band",
        track_title="The Weight",
    )
    uri2 = spotify_resolve_with_streaming_catalog_cache(
        cache,
        client,
        token,
        artist="The Band",
        track_title="The Weight",
    )
    assert uri1 == "spotify:track:cachedtest"
    assert uri2 == "spotify:track:cachedtest"
    assert calls["n"] == 1


def test_spotify_resolve_with_cache_does_not_store_misses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unresolved tracks are not cached; each call still invokes strict resolver."""
    calls = {"n": 0}

    def fake_strict(
        _client: object,
        _token: object,
        *,
        artist: str,
        track_title: str,
    ) -> str | None:
        calls["n"] += 1
        return None

    monkeypatch.setattr(scc_mod, "resolve_track_uri_strict", fake_strict)
    cache = StreamingCatalogCache(tmp_path / "c.sqlite", enabled=True)
    client = MagicMock()
    token = MagicMock()
    assert (
        spotify_resolve_with_streaming_catalog_cache(
            cache, client, token, artist="X", track_title="Y"
        )
        is None
    )
    assert (
        spotify_resolve_with_streaming_catalog_cache(
            cache, client, token, artist="X", track_title="Y"
        )
        is None
    )
    assert calls["n"] == 2


def test_spotify_resolve_with_cache_disabled_calls_strict_each_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When cache is disabled, every resolve hits the strict resolver."""
    calls = {"n": 0}

    def fake_strict(
        _client: object,
        _token: object,
        *,
        artist: str,
        track_title: str,
    ) -> str:
        calls["n"] += 1
        return "spotify:track:x"

    monkeypatch.setattr(scc_mod, "resolve_track_uri_strict", fake_strict)
    cache = StreamingCatalogCache(tmp_path / "c.sqlite", enabled=False)
    client = MagicMock()
    token = MagicMock()
    spotify_resolve_with_streaming_catalog_cache(
        cache, client, token, artist="A", track_title="B"
    )
    spotify_resolve_with_streaming_catalog_cache(
        cache, client, token, artist="A", track_title="B"
    )
    assert calls["n"] == 2


def test_streaming_catalog_cache_enabled_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env flag ``STREAMING_CATALOG_CACHE=0`` disables the cache."""
    monkeypatch.delenv("STREAMING_CATALOG_CACHE", raising=False)
    assert streaming_catalog_cache_enabled_from_env() is True
    monkeypatch.setenv("STREAMING_CATALOG_CACHE", "0")
    assert streaming_catalog_cache_enabled_from_env() is False
    monkeypatch.setenv("STREAMING_CATALOG_CACHE", "false")
    assert streaming_catalog_cache_enabled_from_env() is False


def test_resolve_streaming_catalog_cache_path_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``MUSIC_REVIEW_STREAMING_CACHE_PATH`` sets a relative path under project root."""
    root = tmp_path / "proj"
    root.mkdir()
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(root))
    monkeypatch.setenv("MUSIC_REVIEW_STREAMING_CACHE_PATH", "custom/cache.sqlite")
    assert resolve_streaming_catalog_cache_path() == root / "custom" / "cache.sqlite"


def test_default_streaming_catalog_cache_path_uses_project_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default path lives under ``data/`` at project root."""
    root = tmp_path / "r"
    root.mkdir()
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(root))
    expected = root / "data" / "streaming_catalog_cache.sqlite"
    assert default_streaming_catalog_cache_path() == expected


def test_load_streaming_catalog_cache_from_env_respects_disable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory returns a disabled instance when env disables the feature."""
    monkeypatch.setenv("MUSIC_REVIEW_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("MUSIC_REVIEW_STREAMING_CACHE_PATH", str(tmp_path / "x.sqlite"))
    monkeypatch.setenv("STREAMING_CATALOG_CACHE", "off")
    cache = load_streaming_catalog_cache_from_env()
    assert cache.enabled is False
