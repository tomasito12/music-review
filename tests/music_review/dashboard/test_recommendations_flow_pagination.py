"""Tests für Empfehlungs-Paginierung (ohne Streamlit)."""

from __future__ import annotations

import json

import pytest

from music_review.dashboard.recommendations_flow_pagination import (
    clamp_recommendation_page,
    count_albums_on_next_page,
    parse_page_size_choice,
    recommendation_page_slice_bounds,
    recommendation_total_pages,
    streamlit_parent_scroll_to_anchor_html,
)


class TestRecommendationTotalPages:
    def test_empty_total(self) -> None:
        assert recommendation_total_pages(total=0, page_size=25) == 1

    def test_exact_multiple(self) -> None:
        assert recommendation_total_pages(total=100, page_size=25) == 4

    def test_partial_last_page(self) -> None:
        assert recommendation_total_pages(total=101, page_size=25) == 5
        assert recommendation_total_pages(total=1, page_size=25) == 1


class TestRecommendationPageSliceBounds:
    def test_total_zero(self) -> None:
        assert recommendation_page_slice_bounds(
            page_one_based=1,
            page_size=25,
            total=0,
        ) == (0, 0)

    def test_first_page(self) -> None:
        assert recommendation_page_slice_bounds(
            page_one_based=1,
            page_size=25,
            total=100,
        ) == (0, 25)

    def test_second_page(self) -> None:
        assert recommendation_page_slice_bounds(
            page_one_based=2,
            page_size=25,
            total=100,
        ) == (25, 50)

    def test_last_page_partial(self) -> None:
        assert recommendation_page_slice_bounds(
            page_one_based=4,
            page_size=25,
            total=80,
        ) == (75, 80)

    def test_page_beyond_range_empty_slice(self) -> None:
        assert recommendation_page_slice_bounds(
            page_one_based=10,
            page_size=25,
            total=80,
        ) == (80, 80)


class TestClampRecommendationPage:
    def test_clamp_low(self) -> None:
        assert clamp_recommendation_page(0, 5) == 1
        assert clamp_recommendation_page(-3, 5) == 1

    def test_clamp_high(self) -> None:
        assert clamp_recommendation_page(99, 5) == 5

    def test_within_range(self) -> None:
        assert clamp_recommendation_page(3, 5) == 3


class TestCountAlbumsOnNextPage:
    def test_from_first_page(self) -> None:
        assert (
            count_albums_on_next_page(
                current_page_one_based=1,
                page_size=25,
                total=100,
            )
            == 25
        )

    def test_last_chunk_smaller_than_page_size(self) -> None:
        assert (
            count_albums_on_next_page(
                current_page_one_based=3,
                page_size=25,
                total=80,
            )
            == 5
        )

    def test_on_last_page(self) -> None:
        assert (
            count_albums_on_next_page(
                current_page_one_based=4,
                page_size=25,
                total=80,
            )
            == 0
        )


class TestStreamlitParentScrollToAnchorHtml:
    def test_embeds_json_escaped_id(self) -> None:
        raw_id = 'foo"bar'
        html_snippet = streamlit_parent_scroll_to_anchor_html(
            anchor_element_id=raw_id,
        )
        assert "getElementById" in html_snippet
        assert json.dumps(raw_id) in html_snippet

    def test_falls_back_to_main_scroll_in_script(self) -> None:
        html_snippet = streamlit_parent_scroll_to_anchor_html(
            anchor_element_id="stable-id",
        )
        assert "stAppViewContainer" in html_snippet
        assert "scrollTo" in html_snippet


class TestParsePageSizeChoice:
    def test_numeric_strings(self) -> None:
        assert parse_page_size_choice("25") == 25
        assert parse_page_size_choice(" 100 ") == 100

    def test_alle_case_insensitive(self) -> None:
        assert parse_page_size_choice("Alle") is None
        assert parse_page_size_choice("ALLE") is None

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_page_size_choice("")
