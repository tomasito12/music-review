"""Shared helpers for loading committed test fixture files."""

from __future__ import annotations

from pathlib import Path

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"


def fixture_path(*parts: str) -> Path:
    """Return an absolute path to a file under ``tests/fixtures/``."""
    return FIXTURES_ROOT.joinpath(*parts)
