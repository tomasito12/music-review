"""Tests for newest-batch score histogram helpers."""

from __future__ import annotations

from music_review.dashboard.neueste_batch_score_chart import (
    build_newest_batch_score_figure,
    newest_batch_score_caption,
    newest_batch_score_chart_config,
)


class TestNewestBatchScoreCaption:
    def test_empty_returns_empty_string(self) -> None:
        assert newest_batch_score_caption([]) == ""

    def test_high_batch_suggests_good_fit(self) -> None:
        scores = [0.92, 0.88, 0.75, 0.71, 0.65, 0.62]
        text = newest_batch_score_caption(scores)
        assert "gut zu deinem Profil" in text
        assert "dicht" in text.lower()

    def test_low_batch_suggests_distant(self) -> None:
        scores = [0.12, 0.18, 0.22, 0.25, 0.28, 0.31]
        text = newest_batch_score_caption(scores)
        assert "weiter weg" in text
        assert "durchmischt" in text.lower()

    def test_mixed_batch_neutral_wording(self) -> None:
        scores = [0.5, 0.51, 0.52, 0.53, 0.48, 0.47, 0.46, 0.45]
        text = newest_batch_score_caption(scores)
        assert "mischt" in text.lower() or "Querschnitt" in text

    def test_clamps_out_of_range_values(self) -> None:
        text = newest_batch_score_caption([1.5, -0.3, 0.9])
        assert text


class TestBuildNewestBatchScoreFigure:
    def test_empty_scores_still_returns_figure(self) -> None:
        fig = build_newest_batch_score_figure([])
        assert fig.layout.height is not None
        assert "Passung" in (fig.layout.xaxis.title.text or "")

    def test_bar_trace_with_expected_axes(self) -> None:
        fig = build_newest_batch_score_figure([0.1, 0.2, 0.45, 0.9, 0.91])
        assert len(fig.data) >= 1
        assert fig.data[0].type == "bar"
        y_title = fig.layout.yaxis.title.text if fig.layout.yaxis.title else ""
        assert "Anzahl" in (y_title or "")

    def test_chart_config_hides_mode_bar(self) -> None:
        cfg = newest_batch_score_chart_config()
        assert cfg.get("displayModeBar") is False
