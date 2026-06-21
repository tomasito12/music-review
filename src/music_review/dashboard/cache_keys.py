"""Small helpers for cache keys tied to local data files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

FileCacheSignature = tuple[bool, int, int]


def file_cache_signature(path: str | Path) -> FileCacheSignature:
    """Return a stable cache key that changes when a file changes."""
    file_path = Path(path)
    try:
        stat = file_path.stat()
    except FileNotFoundError:
        return (False, 0, 0)
    return (True, stat.st_mtime_ns, stat.st_size)


def call_file_cached[T](
    cached_fn: Callable[[FileCacheSignature], T],
    path: str | Path,
) -> T:
    """Invoke a ``@st.cache_data`` loader with a signature from ``path``."""
    return cached_fn(file_cache_signature(path))
