# music_review/config.py

"""Shared configuration and environment setup."""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass


def get_project_root() -> Path:
    """Return the project root directory.

    Prefers MUSIC_REVIEW_PROJECT_ROOT env var. Falls back to current working
    directory.
    """
    from os import getenv

    if root := getenv("MUSIC_REVIEW_PROJECT_ROOT"):
        return Path(root).resolve()
    return Path.cwd()


def resolve_data_path(path: str | Path) -> Path:
    """Resolve a data path relative to the project root.

    If the path is absolute, it is returned as-is. Otherwise it is resolved
    against get_project_root(), so data paths work regardless of cwd.
    """
    p = Path(path)
    if p.is_absolute():
        return p
    return get_project_root() / p
