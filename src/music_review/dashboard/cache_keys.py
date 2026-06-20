"""Small helpers for cache keys tied to local data files."""

from __future__ import annotations

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
