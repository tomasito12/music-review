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

    Prefers PROJECT_ROOT env var. Falls back to current working directory.
    """
    from os import getenv

    if root := getenv("MUSIC_REVIEW_PROJECT_ROOT"):
        return Path(root).resolve()
    return Path.cwd()
