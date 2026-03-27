"""Tests for shared Streamlit page helpers (pure logic only)."""

from __future__ import annotations

from datetime import date, datetime

from pages.page_helpers import format_release_date


class TestFormatReleaseDate:
    def test_date_object(self) -> None:
        d = date(2024, 3, 15)
        assert format_release_date(d, None) == "15.03.2024"

    def test_datetime_object(self) -> None:
        dt = datetime(2023, 12, 1, 10, 30)
        assert format_release_date(dt, None) == "01.12.2023"

    def test_iso_string(self) -> None:
        assert format_release_date("2022-06-30", None) == "30.06.2022"

    def test_falls_back_to_release_year(self) -> None:
        assert format_release_date(None, 2021) == "2021"

    def test_falls_back_to_release_year_float(self) -> None:
        assert format_release_date(None, 2020.0) == "2020"

    def test_both_none_returns_empty(self) -> None:
        assert format_release_date(None, None) == ""

    def test_invalid_string_falls_back_to_year(self) -> None:
        assert format_release_date("not-a-date", 2019) == "2019"

    def test_invalid_both_returns_empty(self) -> None:
        assert format_release_date("not-a-date", None) == ""
