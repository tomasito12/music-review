"""Tests for test fixture path helpers."""

from __future__ import annotations

from tests.fixture_paths import FIXTURES_ROOT, fixture_path


def test_fixture_path_resolves_under_tests_fixtures() -> None:
    """Fixture paths always point into the committed tests/fixtures tree."""
    path = fixture_path("commons", "imageinfo_cc_by.json")
    assert path == FIXTURES_ROOT / "commons" / "imageinfo_cc_by.json"
    assert path.is_file()
