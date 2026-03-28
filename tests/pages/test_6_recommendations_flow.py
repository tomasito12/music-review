"""Tests for recommendation card helpers (pure logic, no Streamlit)."""

from __future__ import annotations

from datetime import date

from pages.page_helpers import (
    recommendation_card_community_tags_html,
    recommendation_card_meta_parts,
)


class TestRecommendationCardMetaParts:
    def test_all_fields_present(self) -> None:
        parts = recommendation_card_meta_parts(
            date(2024, 3, 15),
            2024,
            8.0,
            0.87,
            "Indie, Rock",
        )
        assert parts[0] == "15.03.2024"
        assert "8/10" in parts[1]
        assert "0.87" in parts[2]
        assert parts[3] == "Indie, Rock"

    def test_no_rating_uses_default(self) -> None:
        parts = recommendation_card_meta_parts(
            None, 2020, None, 0.5, "", default_rating=5.0
        )
        assert "angenommen" in parts[1]
        assert "5/10" in parts[1]

    def test_no_labels_excluded(self) -> None:
        parts = recommendation_card_meta_parts(None, 2020, 7.0, 0.5, "")
        assert len(parts) == 3

    def test_no_release_date_excluded(self) -> None:
        parts = recommendation_card_meta_parts(None, None, 7.0, 0.5, "Pop")
        assert parts[0].startswith("Rating")

    def test_score_rounded_to_two_decimals(self) -> None:
        parts = recommendation_card_meta_parts(None, None, 7.0, 0.8765, "")
        assert "0.88" in parts[1] or "0.88" in parts[-1]


class TestRecommendationCardCommunityTagsHtml:
    def test_contains_tag_labels(self) -> None:
        tags = [
            {"label": "Indie Rock", "affinity": 0.7},
            {"label": "Post-Punk", "affinity": 0.2},
        ]
        result = recommendation_card_community_tags_html(tags)
        assert "Indie Rock" in result
        assert "Post-Punk" in result
        assert "rec-communities" in result

    def test_high_affinity_dark_red(self) -> None:
        tags = [{"label": "Jazz", "affinity": 0.8}]
        result = recommendation_card_community_tags_html(tags)
        assert "#7f1d1d" in result

    def test_medium_affinity_mid_red(self) -> None:
        tags = [{"label": "Pop", "affinity": 0.4}]
        result = recommendation_card_community_tags_html(tags)
        assert "#dc2626" in result

    def test_low_affinity_light_red(self) -> None:
        tags = [{"label": "Ambient", "affinity": 0.15}]
        result = recommendation_card_community_tags_html(tags)
        assert "#fecaca" in result

    def test_very_low_affinity_neutral(self) -> None:
        tags = [{"label": "Noise", "affinity": 0.05}]
        result = recommendation_card_community_tags_html(tags)
        assert "#f3f4f6" in result

    def test_empty_list(self) -> None:
        result = recommendation_card_community_tags_html([])
        assert "rec-communities" in result
        assert "rec-comm-tag" not in result
