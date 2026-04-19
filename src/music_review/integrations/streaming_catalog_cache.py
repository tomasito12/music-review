"""Deployment-wide cache of streaming-provider track IDs keyed by review metadata.

Maps a stable ``(provider, lookup_key)`` to an external URI (e.g. ``spotify:track:…``).
Lookup keys come from ``catalog_lookup_key`` in ``newest_spotify_playlist`` so they
match playlist duplicate detection.

Disable with env ``STREAMING_CATALOG_CACHE=0`` (also ``false`` / ``no`` / ``off``).
Override the SQLite path with ``MUSIC_REVIEW_STREAMING_CACHE_PATH`` (absolute or
relative paths are supported).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from typing import Final

from music_review.config import get_project_root
from music_review.dashboard.newest_deezer_playlist import (
    resolve_track_uri_strict as deezer_resolve_track_uri_strict,
)
from music_review.dashboard.newest_spotify_playlist import (
    catalog_lookup_key,
    resolve_track_uri_strict,
)
from music_review.integrations.deezer_client import DeezerClient, DeezerToken
from music_review.integrations.spotify_client import SpotifyClient, SpotifyToken

LOGGER = logging.getLogger(__name__)

PROVIDER_SPOTIFY: Final[str] = "spotify"
PROVIDER_DEEZER: Final[str] = "deezer"

_ENV_DISABLE_FLAG: Final[str] = "STREAMING_CATALOG_CACHE"
_ENV_PATH_OVERRIDE: Final[str] = "MUSIC_REVIEW_STREAMING_CACHE_PATH"

_DEFAULT_DB_NAME: Final[str] = "streaming_catalog_cache.sqlite"


def _falsy_env(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"0", "false", "no", "off"}


def default_streaming_catalog_cache_path() -> Path:
    """Return the default SQLite path under ``data/`` in the project root."""
    return get_project_root() / "data" / _DEFAULT_DB_NAME


def resolve_streaming_catalog_cache_path() -> Path:
    """Resolve DB path from ``MUSIC_REVIEW_STREAMING_CACHE_PATH`` or default."""
    override = (getenv(_ENV_PATH_OVERRIDE) or "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else (get_project_root() / p)
    return default_streaming_catalog_cache_path()


def streaming_catalog_cache_enabled_from_env() -> bool:
    """Return False when ``STREAMING_CATALOG_CACHE`` disables the feature."""
    raw = getenv(_ENV_DISABLE_FLAG)
    return not (raw is not None and _falsy_env(raw))


class StreamingCatalogCache:
    """SQLite-backed lookup for one external URI per (provider, lookup_key)."""

    def __init__(self, db_path: Path, *, enabled: bool = True) -> None:
        self._db_path = db_path
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """When False, :meth:`get` always returns None and :meth:`put` is a no-op."""
        return self._enabled

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_entries (
                provider TEXT NOT NULL,
                lookup_key TEXT NOT NULL,
                external_uri TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (provider, lookup_key)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_catalog_provider_key "
            "ON catalog_entries (provider, lookup_key)"
        )

    def get(self, provider: str, lookup_key: str) -> str | None:
        """Return cached ``external_uri`` or None when missing or disabled."""
        if not self._enabled:
            return None
        p = provider.strip()
        k = lookup_key.strip()
        if not p or not k:
            return None
        try:
            with self._connect() as conn:
                self._ensure_schema(conn)
                row = conn.execute(
                    "SELECT external_uri FROM catalog_entries "
                    "WHERE provider = ? AND lookup_key = ?",
                    (p, k),
                ).fetchone()
        except OSError as exc:
            LOGGER.warning(
                "streaming catalog cache read failed path=%s: %s",
                self._db_path,
                exc,
            )
            return None
        if row is None:
            return None
        uri = row[0]
        return uri if isinstance(uri, str) and uri else None

    def put(self, provider: str, lookup_key: str, external_uri: str) -> None:
        """Upsert a mapping. No-op when disabled or inputs are empty."""
        if not self._enabled:
            return
        p = provider.strip()
        k = lookup_key.strip()
        uri = external_uri.strip()
        if not p or not k or not uri:
            return
        now = datetime.now(tz=UTC).isoformat()
        try:
            with self._connect() as conn:
                self._ensure_schema(conn)
                conn.execute(
                    """
                    INSERT INTO catalog_entries (
                        provider, lookup_key, external_uri, updated_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(provider, lookup_key) DO UPDATE SET
                        external_uri = excluded.external_uri,
                        updated_at = excluded.updated_at
                    """,
                    (p, k, uri, now),
                )
                conn.commit()
        except OSError as exc:
            LOGGER.warning(
                "streaming catalog cache write failed path=%s: %s",
                self._db_path,
                exc,
            )


def load_streaming_catalog_cache_from_env() -> StreamingCatalogCache:
    """Build a cache instance from environment (path + enable flag)."""
    enabled = streaming_catalog_cache_enabled_from_env()
    path = resolve_streaming_catalog_cache_path()
    if not enabled:
        LOGGER.info(
            "streaming catalog cache disabled via %s",
            _ENV_DISABLE_FLAG,
        )
    else:
        LOGGER.debug(
            "streaming catalog cache enabled path=%s",
            path,
        )
    return StreamingCatalogCache(path, enabled=enabled)


def spotify_resolve_with_streaming_catalog_cache(
    cache: StreamingCatalogCache,
    client: SpotifyClient,
    token: SpotifyToken,
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Resolve a Spotify URI via strict search, using the catalog cache."""
    key = catalog_lookup_key(artist, track_title)
    if cache.enabled:
        hit = cache.get(PROVIDER_SPOTIFY, key)
        if hit is not None:
            LOGGER.debug(
                "streaming catalog cache hit provider=%s key_prefix=%s",
                PROVIDER_SPOTIFY,
                key[:120],
            )
            return hit
    uri = resolve_track_uri_strict(
        client,
        token,
        artist=artist,
        track_title=track_title,
    )
    if uri and cache.enabled:
        cache.put(PROVIDER_SPOTIFY, key, uri)
    return uri


def deezer_resolve_with_streaming_catalog_cache(
    cache: StreamingCatalogCache,
    client: DeezerClient,
    token: DeezerToken,
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Resolve a Deezer URI via strict search, using the catalog cache.

    Deezer URIs are stored as ``deezer:track:{numeric_id}`` so they never
    collide with Spotify URIs in the shared per-(provider, key) cache.
    """
    key = catalog_lookup_key(artist, track_title)
    if cache.enabled:
        hit = cache.get(PROVIDER_DEEZER, key)
        if hit is not None:
            LOGGER.debug(
                "streaming catalog cache hit provider=%s key_prefix=%s",
                PROVIDER_DEEZER,
                key[:120],
            )
            return hit
    uri = deezer_resolve_track_uri_strict(
        client,
        token,
        artist=artist,
        track_title=track_title,
    )
    if uri and cache.enabled:
        cache.put(PROVIDER_DEEZER, key, uri)
    return uri
