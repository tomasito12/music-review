"""Tests for shared Streamlit page helpers (pure logic only)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pages.page_helpers import (
    OVERALL_WEIGHT_TRADEOFF_RED_DARK,
    OVERALL_WEIGHT_TRADEOFF_RED_LIGHT,
    OVERALL_WEIGHT_TRADEOFF_RED_MID,
    PLATTENLABEL_SONSTIGE_UI,
    SPECTRUM_CROSSOVER_STOPS,
    STYLE_MATCH_FILTER_PERCENT_STEP,
    build_community_broad_category_index,
    clamp_plattentests_rating_filter_range,
    clamp_year_filter_bounds,
    collapse_plattenlabel_ui_selection,
    community_display_label,
    expand_plattenlabel_ui_selection,
    format_record_labels_for_card,
    format_release_date,
    format_style_match_range_display,
    max_release_year_in_jsonl,
    min_release_year_in_jsonl,
    normalize_filter_expander_vspace_gap,
    overall_weights_display_percents,
    overall_weights_tradeoff_bar_html,
    plattenlabel_album_count_buckets_from_reviews_jsonl,
    plattenlabel_filter_passes,
    recommendation_card_community_tags_html,
    recommendation_card_meta_parts,
    recommendation_flow_shell_css_rules,
    release_year_for_card_meta,
    review_raw_release_year,
    search_rag_hits_for_dashboard,
    snap_spectrum_crossover,
    spectrum_crossover_option_label,
    spectrum_crossover_semantic_label,
    style_match_percent_tuple_for_slider,
    style_match_scores_from_percent_slider,
    unique_plattenlabels_from_reviews_jsonl,
)


class TestPlattenlabelAlbumCountBuckets:
    def test_individual_only_if_more_than_threshold(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = [f'{{"id": {i}, "labels": ["A"]}}\n' for i in range(3)]
        lines += [f'{{"id": {i}, "labels": ["B"]}}\n' for i in range(3, 5)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
            p,
            min_albums_exclusive=2,
        )
        assert n == 5
        assert freq == ["A"]
        assert rare == ["B"]

    def test_exactly_threshold_is_sonstige(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = [f'{{"id": {i}, "labels": ["X"]}}\n' for i in range(2)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
            p,
            min_albums_exclusive=2,
        )
        assert n == 2
        assert freq == []
        assert rare == ["X"]

    def test_default_threshold_fifty_one_albums(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = [f'{{"id": {i}, "labels": ["Heavy"]}}\n' for i in range(51)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(p)
        assert n == 51
        assert freq == ["Heavy"]
        assert rare == []

    def test_default_fifty_exactly_is_sonstige(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = [f'{{"id": {i}, "labels": ["Edge"]}}\n' for i in range(50)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(p)
        assert n == 50
        assert freq == []
        assert rare == ["Edge"]

    def test_frequent_sorted_by_count_then_name(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = [f'{{"id": {i}, "labels": ["Hi"]}}\n' for i in range(5)]
        lines += [f'{{"id": {i}, "labels": ["Lo"]}}\n' for i in range(5, 8)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
            p,
            min_albums_exclusive=2,
        )
        assert n == 8
        assert freq == ["Hi", "Lo"]
        assert rare == []

    def test_dedupes_labels_within_one_review(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        lines = ['{"id": 0, "labels": ["Z", "Z"]}\n']
        lines += [f'{{"id": {i}, "labels": ["Z"]}}\n' for i in range(1, 4)]
        p.write_text("".join(lines), encoding="utf-8")
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
            p,
            min_albums_exclusive=2,
        )
        assert n == 4
        assert freq == ["Z"]
        assert rare == []

    def test_multi_label_album_each_label_counted(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        p.write_text(
            '{"id": 0, "labels": ["EU_Label", "US_Label"]}\n',
            encoding="utf-8",
        )
        freq, rare, n = plattenlabel_album_count_buckets_from_reviews_jsonl(
            p,
            min_albums_exclusive=0,
        )
        assert n == 1
        assert freq == ["EU_Label", "US_Label"]
        assert rare == []


class TestExpandCollapsePlattenlabelUi:
    def test_expand_sonstige_adds_rare(self) -> None:
        out = expand_plattenlabel_ui_selection(
            ["A", PLATTENLABEL_SONSTIGE_UI],
            ["r1", "r2"],
        )
        assert set(out) == {"A", "r1", "r2"}

    def test_collapse_full_rare_adds_sonstige(self) -> None:
        ui = collapse_plattenlabel_ui_selection(
            {"A", "r1", "r2"},
            frequent=["A"],
            rare=["r1", "r2"],
        )
        assert PLATTENLABEL_SONSTIGE_UI in ui
        assert "A" in ui

    def test_roundtrip(self) -> None:
        freq = ["F1"]
        rare = ["R1", "R2"]
        ui = [freq[0], PLATTENLABEL_SONSTIGE_UI]
        concrete = set(expand_plattenlabel_ui_selection(ui, rare))
        back = collapse_plattenlabel_ui_selection(concrete, freq, rare)
        assert set(back) == set(ui)


class TestUniquePlattenlabelsFromReviewsJsonl:
    def test_collects_sorted_unique_labels(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        p.write_text(
            '{"id": 1, "labels": ["B", "A"]}\n{"id": 2, "labels": ["A", "  "]}\n',
            encoding="utf-8",
        )
        assert unique_plattenlabels_from_reviews_jsonl(p) == ["A", "B"]

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "missing.jsonl"
        assert unique_plattenlabels_from_reviews_jsonl(p) == []


class TestPlattenlabelFilterPasses:
    def test_no_corpus_labels_always_passes(self) -> None:
        assert plattenlabel_filter_passes(["X"], None, []) is True
        assert plattenlabel_filter_passes(["X"], [], []) is True

    def test_missing_selection_no_filter(self) -> None:
        all_l = ["A", "B"]
        assert plattenlabel_filter_passes(["A"], None, all_l) is True
        assert plattenlabel_filter_passes(["A"], "bad", all_l) is True

    def test_all_selected_no_filter(self) -> None:
        all_l = ["A", "B"]
        assert plattenlabel_filter_passes(["Z"], ["A", "B"], all_l) is True

    def test_empty_selection_only_unlabeled(self) -> None:
        all_l = ["A", "B"]
        assert plattenlabel_filter_passes([], [], all_l) is True
        assert plattenlabel_filter_passes(["A"], [], all_l) is False

    def test_partial_or_semantics(self) -> None:
        all_l = ["A", "B", "C"]
        assert plattenlabel_filter_passes(["A", "B"], ["B"], all_l) is True
        assert plattenlabel_filter_passes(["C"], ["A"], all_l) is False

    def test_unlabeled_album_passes_when_partial(self) -> None:
        all_l = ["A", "B"]
        assert plattenlabel_filter_passes([], ["A"], all_l) is True


class TestFormatRecordLabelsForCard:
    def test_prefers_metadata_list(self) -> None:
        assert format_record_labels_for_card(["A", "B"], ["Scraped"]) == "A, B"

    def test_falls_back_to_review_labels(self) -> None:
        assert format_record_labels_for_card([], ["Sub Pop"]) == "Sub Pop"
        assert format_record_labels_for_card(None, ["  X  ", ""]) == "X"

    def test_metadata_string_used_verbatim(self) -> None:
        assert format_record_labels_for_card("Foo, Bar", ["Z"]) == "Foo, Bar"

    def test_empty_when_no_source(self) -> None:
        assert format_record_labels_for_card([], []) == ""
        assert format_record_labels_for_card("", None) == ""


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


class TestCommunityDisplayLabel:
    def test_uses_genre_label_when_present(self) -> None:
        assert (
            community_display_label(
                "C001",
                {"C001": "Shoegaze"},
                None,
            )
            == "Shoegaze"
        )

    def test_falls_back_to_centroid(self) -> None:
        assert (
            community_display_label(
                "C002",
                {},
                {"id": "C002", "centroid": "Artist A"},
            )
            == "Artist A"
        )

    def test_genre_label_wins_over_centroid(self) -> None:
        assert (
            community_display_label(
                "C003",
                {"C003": "Post-Punk"},
                {"id": "C003", "centroid": "Other"},
            )
            == "Post-Punk"
        )

    def test_generic_when_no_label_or_centroid(self) -> None:
        assert community_display_label("C099", {}, None) == "Stil-Cluster"

    def test_empty_community_dict_without_genre(self) -> None:
        assert community_display_label("C100", {}, {}) == "Stil-Cluster"


class TestBuildCommunityBroadCategoryIndex:
    def test_empty_input_returns_empty_dict(self) -> None:
        assert build_community_broad_category_index([], {}, {}) == {}

    def test_skips_community_without_id(self) -> None:
        communities = [{"top_artists": ["A"]}]
        assert build_community_broad_category_index(communities, {}, {}) == {}

    def test_maps_to_sonstige_when_no_category(self) -> None:
        communities = [
            {
                "id": "C001",
                "top_artists": ["Artist A"],
            },
        ]
        out = build_community_broad_category_index(communities, {"C001": "Rock"}, {})
        assert list(out.keys()) == ["Sonstige"]
        assert len(out["Sonstige"]) == 1
        row = out["Sonstige"][0]
        assert row["id"] == "C001"
        assert row["genre_label"] == "Rock"
        assert row["top_artists"] == ["Artist A"]

    def test_splits_across_multiple_categories(self) -> None:
        communities = [
            {
                "id": "C002",
                "top_artists": ["B"],
            },
        ]
        mappings = {"C002": ["A", "B"]}
        out = build_community_broad_category_index(
            communities,
            {"C002": "Jazz"},
            mappings,
        )
        assert set(out.keys()) == {"A", "B"}
        assert out["A"][0]["id"] == "C002"
        assert out["B"][0]["id"] == "C002"

    def test_sorts_rows_by_genre_label_case_insensitive(self) -> None:
        communities = [
            {"id": "C1", "top_artists": []},
            {"id": "C2", "top_artists": []},
        ]
        labels = {"C1": "zebra", "C2": "Alpha"}
        out = build_community_broad_category_index(communities, labels, {})
        names = [r["genre_label"] for r in out["Sonstige"]]
        assert names == ["Alpha", "zebra"]


class TestClampPlattentestsRatingFilterRange:
    def test_defaults_to_full_scale(self) -> None:
        assert clamp_plattentests_rating_filter_range(0, 10) == (0, 10)

    def test_rounds_floats_to_integers(self) -> None:
        assert clamp_plattentests_rating_filter_range(2.4, 8.6) == (2, 9)

    def test_clamps_to_zero_ten(self) -> None:
        assert clamp_plattentests_rating_filter_range(-3, 15) == (0, 10)

    def test_swaps_when_min_exceeds_max(self) -> None:
        assert clamp_plattentests_rating_filter_range(9, 3) == (3, 9)

    def test_invalid_values_fall_back(self) -> None:
        assert clamp_plattentests_rating_filter_range("x", "y") == (7, 10)


class TestReviewRawReleaseYear:
    def test_uses_release_year_field(self) -> None:
        assert review_raw_release_year({"release_year": 2018}) == 2018

    def test_uses_iso_release_date_prefix(self) -> None:
        assert review_raw_release_year({"release_date": "2021-03-15"}) == 2021

    def test_empty_returns_none(self) -> None:
        assert review_raw_release_year({}) is None

    def test_invalid_year_ignored(self) -> None:
        assert review_raw_release_year({"release_year": 99999}) is None


class TestMaxReleaseYearInJsonl:
    def test_returns_max_from_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        p.write_text(
            '{"release_year": 2005, "id": 1}\n{"release_year": 2024, "id": 2}\n',
            encoding="utf-8",
        )
        assert max_release_year_in_jsonl(p) == 2024

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert max_release_year_in_jsonl(tmp_path / "missing.jsonl") is None


class TestMinReleaseYearInJsonl:
    def test_returns_min_from_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "reviews.jsonl"
        p.write_text(
            '{"release_year": 1988, "id": 1}\n{"release_year": 2005, "id": 2}\n',
            encoding="utf-8",
        )
        assert min_release_year_in_jsonl(p) == 1988

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert min_release_year_in_jsonl(tmp_path / "missing.jsonl") is None


class TestClampYearFilterBounds:
    def test_clamps_high_max_to_cap(self) -> None:
        assert clamp_year_filter_bounds(1990, 2030, year_cap=2025) == (1990, 2025)

    def test_swaps_when_min_exceeds_max(self) -> None:
        assert clamp_year_filter_bounds(2010, 2000, year_cap=2025) == (2000, 2010)

    def test_invalid_falls_back(self) -> None:
        lo, hi = clamp_year_filter_bounds("x", "y", year_cap=2020)
        assert lo == 1990
        assert hi == 2020


class TestNormalizeFilterExpanderVspaceGap:
    def test_accepts_defined_sizes(self) -> None:
        assert normalize_filter_expander_vspace_gap("sm") == "sm"
        assert normalize_filter_expander_vspace_gap("xl") == "xl"

    def test_unknown_string_falls_back_to_md(self) -> None:
        assert normalize_filter_expander_vspace_gap("huge") == "md"


class TestStyleMatchPercentTupleForSlider:
    def test_full_range_default(self) -> None:
        assert style_match_percent_tuple_for_slider(0.0, 1.0) == (0, 100)

    def test_snaps_to_step(self) -> None:
        lo, hi = style_match_percent_tuple_for_slider(
            0.37,
            0.82,
            step=STYLE_MATCH_FILTER_PERCENT_STEP,
        )
        assert lo == 35
        assert hi == 80

    def test_swaps_when_min_score_above_max(self) -> None:
        lo, hi = style_match_percent_tuple_for_slider(0.9, 0.1)
        assert lo <= hi
        assert (lo, hi) == (10, 90)

    def test_invalid_strings_use_safe_defaults(self) -> None:
        lo, hi = style_match_percent_tuple_for_slider("x", "y")
        assert (lo, hi) == (0, 100)


class TestStyleMatchScoresFromPercentSlider:
    def test_round_trip_percent(self) -> None:
        assert style_match_scores_from_percent_slider(25, 75) == (0.25, 0.75)

    def test_swaps_when_reversed(self) -> None:
        assert style_match_scores_from_percent_slider(80, 20) == (0.2, 0.8)


class TestFormatStyleMatchRangeDisplay:
    def test_formats_scores_as_percent_phrase(self) -> None:
        assert format_style_match_range_display(0.35, 1.0) == "35 % bis 100 %"

    def test_orders_when_reversed(self) -> None:
        assert format_style_match_range_display(0.9, 0.1) == "10 % bis 90 %"


class TestSpectrumCrossoverStops:
    def test_stops_cover_full_range_with_five_steps(self) -> None:
        assert SPECTRUM_CROSSOVER_STOPS[0] == 0.0
        assert SPECTRUM_CROSSOVER_STOPS[-1] == 1.0
        assert len(SPECTRUM_CROSSOVER_STOPS) == 5

    def test_snap_maps_to_nearest_stop(self) -> None:
        assert snap_spectrum_crossover(0.5) == 0.5
        assert snap_spectrum_crossover(0.37) == 0.25
        assert snap_spectrum_crossover(0.38) == 0.5

    def test_snap_invalid_input_defaults_to_balanced(self) -> None:
        assert snap_spectrum_crossover("nope") == 0.5

    def test_snap_clamps_out_of_range(self) -> None:
        assert snap_spectrum_crossover(-3.0) == 0.0
        assert snap_spectrum_crossover(9.0) == 1.0

    def test_option_label_matches_stop(self) -> None:
        assert spectrum_crossover_option_label(0.5) == "Ausgewogen"
        assert spectrum_crossover_option_label(1.0) == "Breite Abdeckung"

    def test_semantic_label_snaps_before_label(self) -> None:
        assert spectrum_crossover_semantic_label(0.51) == "Ausgewogen"


class TestOverallWeightsDisplayPercents:
    def test_equal_shares_sum_to_100(self) -> None:
        pa, pb, pg = overall_weights_display_percents(1 / 3, 1 / 3, 1 / 3)
        assert pa + pb + pg == 100

    def test_one_hot_corner(self) -> None:
        pa, pb, pg = overall_weights_display_percents(1.0, 0.0, 0.0)
        assert (pa, pb, pg) == (100, 0, 0)

    def test_typical_normalized_vector(self) -> None:
        pa, pb, pg = overall_weights_display_percents(0.5, 0.25, 0.25)
        assert pa + pb + pg == 100
        assert pa == 50
        assert pb == 25
        assert pg == 25


class TestOverallWeightsTradeoffBarHtml:
    def test_includes_percent_segments_in_markup(self) -> None:
        html = overall_weights_tradeoff_bar_html(0.5, 0.25, 0.25)
        assert "50 %" in html
        assert "ow-tradeoff-bar" in html
        assert "Stil-Nähe" in html
        assert OVERALL_WEIGHT_TRADEOFF_RED_LIGHT in html
        assert OVERALL_WEIGHT_TRADEOFF_RED_MID in html
        assert OVERALL_WEIGHT_TRADEOFF_RED_DARK in html


class TestReleaseYearForCardMeta:
    def test_prefers_release_year_attribute(self) -> None:
        r = SimpleNamespace(release_year=2019, release_date=date(2020, 1, 1))
        assert release_year_for_card_meta(r) == 2019

    def test_falls_back_to_date_year(self) -> None:
        r = SimpleNamespace(release_year=None, release_date=date(2021, 6, 15))
        assert release_year_for_card_meta(r) == 2021

    def test_returns_none_when_missing(self) -> None:
        r = SimpleNamespace(release_year=None, release_date=None)
        assert release_year_for_card_meta(r) is None


class TestRecommendationCardMetaPartsIncludeOverallScore:
    def test_omits_score_line_when_disabled(self) -> None:
        parts = recommendation_card_meta_parts(
            None,
            2020,
            7.0,
            0.99,
            "Indie",
            include_overall_score=False,
        )
        assert not any(p.startswith("Score ") for p in parts)
        assert any("Plattenlabel" in p for p in parts)

    def test_rating_only_when_no_score_no_labels(self) -> None:
        parts = recommendation_card_meta_parts(
            None,
            None,
            8.0,
            0.0,
            "",
            include_overall_score=False,
        )
        assert len(parts) == 1
        assert "8/10" in parts[0]


class TestRecommendationFlowShellCssRules:
    def test_includes_hero_card_and_callout_selectors(self) -> None:
        css = recommendation_flow_shell_css_rules()
        assert ".rec-hero" in css
        assert ".rec-card" in css
        assert ".rec-callout-info" in css

    def test_chat_avatar_block_only_when_requested(self) -> None:
        base = recommendation_flow_shell_css_rules()
        assert "chatAvatarIcon-assistant" not in base
        with_avatar = recommendation_flow_shell_css_rules(
            include_chat_avatar_style=True,
        )
        assert "chatAvatarIcon-assistant" in with_avatar

    def test_appends_extra_rules(self) -> None:
        extra = "        .x-test { z: 1; }"
        css = recommendation_flow_shell_css_rules(extra_rules=extra)
        assert ".x-test" in css

    def test_includes_filtered_comm_tag_selector(self) -> None:
        css = recommendation_flow_shell_css_rules()
        assert "rec-comm-tag--filtered" in css
        assert "box-shadow" in css


class TestRecommendationCardCommunityTagsFilteredHighlight:
    def test_adds_filtered_class_when_id_in_filter_set(self) -> None:
        tags = [
            {"id": "C001", "label": "Indie", "affinity": 0.5},
            {"id": "C002", "label": "Jazz", "affinity": 0.2},
        ]
        html = recommendation_card_community_tags_html(
            tags,
            filter_selected_community_ids={"C001"},
        )
        assert "rec-comm-tag--filtered" in html
        assert html.count("rec-comm-tag--filtered") == 1

    def test_no_filtered_class_when_id_not_selected(self) -> None:
        tags = [{"id": "C099", "label": "Noise", "affinity": 0.4}]
        html = recommendation_card_community_tags_html(
            tags,
            filter_selected_community_ids={"C001"},
        )
        assert "rec-comm-tag--filtered" not in html

    def test_empty_filter_does_not_highlight(self) -> None:
        tags = [{"id": "C001", "label": "Pop", "affinity": 0.6}]
        html = recommendation_card_community_tags_html(
            tags,
            filter_selected_community_ids=set(),
        )
        assert "rec-comm-tag--filtered" not in html

    def test_matches_filter_id_casefold_and_trimmed(self) -> None:
        tags = [{"id": " C001 ", "label": "Dream Pop", "affinity": 0.55}]
        html = recommendation_card_community_tags_html(
            tags,
            filter_selected_community_ids={"c001"},
        )
        assert "rec-comm-tag--filtered" in html


class TestSearchRagHitsForDashboard:
    def test_delegates_to_search_reviews_with_variants(self) -> None:
        """Semantic search helper forwards to the vector store with strategy B."""
        fake_hits = [{"review_id": 7, "distance": 0.5}]
        with patch(
            "music_review.pipeline.retrieval.vector_store.search_reviews_with_variants",
            return_value=fake_hits,
        ) as mocked:
            search_rag_hits_for_dashboard.clear()
            out = search_rag_hits_for_dashboard("melodic metal")
        assert out == fake_hits
        mocked.assert_called_once()
        kwargs = mocked.call_args.kwargs
        assert kwargs["strategy"] == "B"
        assert kwargs["n_results"] == 2500
        assert kwargs["top_k_per_variant"] == 2500
