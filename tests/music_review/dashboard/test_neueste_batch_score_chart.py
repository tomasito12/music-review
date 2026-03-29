"""Tests for newest-batch score histogram helpers."""

from __future__ import annotations

from music_review.dashboard.neueste_batch_score_chart import (
    NEWEST_BATCH_SCORE_SCALE_EXPLANATION,
    SCORE_HIST_NUM_BINS,
    build_newest_batch_score_figure,
    newest_batch_score_caption,
    newest_batch_score_chart_config,
    newest_batch_score_scale_explanation,
)


class TestNewestBatchScoreCaption:
    def test_empty_returns_empty_string(self) -> None:
        assert newest_batch_score_caption([]) == ""

    def test_high_batch_suggests_good_fit(self) -> None:
        scores = [0.92, 0.88, 0.75, 0.71, 0.65, 0.62]
        text = newest_batch_score_caption(scores)
        assert "gut zu deinem Profil" in text
        assert "dicht" in text.lower()

    def test_low_batch_returns_empty_string(self) -> None:
        scores = [0.12, 0.18, 0.22, 0.25, 0.28, 0.31]
        text = newest_batch_score_caption(scores)
        assert text == ""

    def test_mixed_batch_returns_empty_string(self) -> None:
        scores = [0.5, 0.51, 0.52, 0.53, 0.48, 0.47, 0.46, 0.45]
        text = newest_batch_score_caption(scores)
        assert text == ""

    def test_clamps_out_of_range_values(self) -> None:
        text = newest_batch_score_caption([1.5, -0.3, 0.9])
        assert text


class TestNewestBatchScoreScaleExplanation:
    def test_matches_constant_and_covers_zero_and_one(self) -> None:
        got = newest_batch_score_scale_explanation()
        assert got == NEWEST_BATCH_SCORE_SCALE_EXPLANATION
        assert "Score von 0" in NEWEST_BATCH_SCORE_SCALE_EXPLANATION
        assert "Score von 1" in NEWEST_BATCH_SCORE_SCALE_EXPLANATION


class TestBuildNewestBatchScoreFigure:
    def test_empty_scores_still_returns_figure(self) -> None:
        fig = build_newest_batch_score_figure([])
        assert fig.layout.height is not None
        title = fig.layout.title.text if fig.layout.title else None
        assert not title

    def test_bar_trace_with_expected_axes(self) -> None:
        fig = build_newest_batch_score_figure([0.1, 0.2, 0.45, 0.9, 0.91])
        assert len(fig.data) >= 1
        assert fig.data[0].type == "bar"
        y_title = fig.layout.yaxis.title.text if fig.layout.yaxis.title else ""
        assert "Anzahl" in (y_title or "")
        title = fig.layout.title.text if fig.layout.title else None
        assert not title
        custom = fig.data[0].customdata
        assert custom is not None and len(custom) > 0
        assert str(custom[0]) == "0.00 - 0.12"
        assert "0,00" not in str(custom[0])
        assert "<br>" not in str(custom[0])

    def test_x_axis_bin_labels_multiline_and_horizontal(self) -> None:
        fig = build_newest_batch_score_figure([0.5])
        xa = fig.layout.xaxis
        assert xa.tickangle == 0
        ticktext = xa.ticktext
        assert ticktext is not None
        assert any(" -<br>" in str(label) for label in ticktext)

    def test_empty_scores_figure_same_x_axis_style(self) -> None:
        fig = build_newest_batch_score_figure([])
        assert fig.layout.xaxis.tickangle == 0
        tt = fig.layout.xaxis.ticktext
        assert tt is not None and any(" -<br>" in str(label) for label in tt)

    def test_chart_config_hides_mode_bar(self) -> None:
        cfg = newest_batch_score_chart_config()
        assert cfg.get("displayModeBar") is False

    def test_bar_colours_follow_score_position_left_to_right(self) -> None:
        fig = build_newest_batch_score_figure([0.1, 0.2, 0.45, 0.9, 0.91])
        colors = fig.data[0].marker.color
        assert colors is not None
        color_list = [str(c).lower() for c in list(colors)]
        assert len(color_list) == SCORE_HIST_NUM_BINS
        assert color_list[0] == "#fecaca"
        assert color_list[-1] == "#b91c1c"
