# music_review/config.py

"""Shared configuration and environment setup."""

from __future__ import annotations

from pathlib import Path


def _project_root_for_dotenv() -> Path | None:
    """Resolve repo root when running from a source checkout (`src/music_review/`)."""
    pkg_dir = Path(__file__).resolve().parent
    if pkg_dir.name != "music_review":
        return None
    src_dir = pkg_dir.parent
    if src_dir.name != "src":
        return None
    root = src_dir.parent
    env_file = root / ".env"
    return root if env_file.is_file() else None


def _load_dotenv_files() -> None:
    """Load `.env` from the project checkout first, then fall back to cwd."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    root = _project_root_for_dotenv()
    if root is not None:
        load_dotenv(root / ".env", override=True)
    else:
        load_dotenv(override=True)


_load_dotenv_files()


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
