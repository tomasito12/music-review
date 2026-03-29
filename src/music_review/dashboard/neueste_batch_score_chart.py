"""Plotly chart and caption for newest-album batch score distribution (Streamlit UI)."""

from __future__ import annotations

import statistics
from typing import Any

import plotly.graph_objects as go

SCORE_HIST_NUM_BINS = 8

# Caption thresholds (share of albums with score >= 0.5, and median).
_CAPTION_HIGH_SHARE = 0.55
_CAPTION_HIGH_MEDIAN = 0.48

# Bar colours: links (niedrige Scores) hell, rechts (hohe Scores) intensiv.
_COLOR_LIGHT = "#fecaca"
_COLOR_DEEP = "#b91c1c"

_CHART_HEIGHT_PX = 292
_VLINE_COLOR = "#991b1b"

# Kurztext unter dem Histogramm (Seite rendert ihn als HTML-Absatz); Skala 0/1.
NEWEST_BATCH_SCORE_SCALE_EXPLANATION = (
    "Ein Score von 0 bedeutet, dass für das Album keine der von dir "
    "präferierten Stil-Richtungen enthalten sind. "
    "Ein Score von 1 bedeutet, dass das Album ausschließlich von dir "
    "präferierte Stil-Richtungen aufweist."
)

_X_AXIS_BOTTOM_MARGIN = 88


def newest_batch_score_scale_explanation() -> str:
    """Kurzer Hilfetext zur Bedeutung der Scores 0 und 1 unter dem Diagramm."""
    return NEWEST_BATCH_SCORE_SCALE_EXPLANATION


def _clamp_unit_interval(values: list[float]) -> list[float]:
    out: list[float] = []
    for raw in values:
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        out.append(max(0.0, min(1.0, v)))
    return out


def _bin_counts(values: list[float], nbins: int) -> list[int]:
    if nbins < 1:
        return []
    counts = [0] * nbins
    for v in values:
        idx = min(int(v * nbins), nbins - 1)
        counts[idx] += 1
    return counts


def _hex_to_rgb(color_hex: str) -> tuple[int, int, int]:
    h = color_hex.removeprefix("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp_hex(light: str, deep: str, t: float) -> str:
    t_clamped = max(0.0, min(1.0, t))
    r0, g0, b0 = _hex_to_rgb(light)
    r1, g1, b1 = _hex_to_rgb(deep)
    r = round(r0 + (r1 - r0) * t_clamped)
    g = round(g0 + (g1 - g0) * t_clamped)
    b = round(b0 + (b1 - b0) * t_clamped)
    return _rgb_to_hex(r, g, b)


def _bar_colours_by_score_position(nbins: int) -> list[str]:
    """Colour ramp by bin position: left light, right deep red."""
    if nbins < 1:
        return []
    if nbins == 1:
        return [_COLOR_DEEP]
    return [_lerp_hex(_COLOR_LIGHT, _COLOR_DEEP, i / (nbins - 1)) for i in range(nbins)]


def _bin_centers(nbins: int) -> list[float]:
    w = 1.0 / nbins
    return [w * (i + 0.5) for i in range(nbins)]


def _bin_axis_and_hover_labels(nbins: int) -> tuple[list[str], list[str]]:
    """Achsen-Ticks mit HTML-Zeilenumbruch (Plotly: ``<br>``); Hover-Text einzeilig."""
    w = 1.0 / nbins
    axis_labels: list[str] = []
    hover_labels: list[str] = []
    for i in range(nbins):
        a = i * w
        b = (i + 1) * w if i < nbins - 1 else 1.0
        a_s = f"{a:.2f}"
        b_s = f"{b:.2f}"
        axis_labels.append(f"{a_s} -<br>{b_s}")
        hover_labels.append(f"{a_s} - {b_s}")
    return axis_labels, hover_labels


def newest_batch_score_caption(scores: list[float]) -> str:
    """Short German line for the batch; empty scores yield an empty string."""
    clamped = _clamp_unit_interval(scores)
    if not clamped:
        return ""
    n = len(clamped)
    high = sum(1 for s in clamped if s >= 0.5)
    share = high / n
    med = float(statistics.median(clamped))

    if share >= _CAPTION_HIGH_SHARE and med >= _CAPTION_HIGH_MEDIAN:
        return (
            "In diesem Ausschnitt passen viele der neuesten Alben gut zu deinem Profil "
            "(eher dicht an deinen Präferenzen)."
        )
    return ""


def build_newest_batch_score_figure(scores: list[float]) -> go.Figure:
    """Bar histogram on [0, 1] with mean vline and rose/red styling."""
    clamped = _clamp_unit_interval(scores)
    nbins = SCORE_HIST_NUM_BINS
    centers = _bin_centers(nbins)
    ticktext_axis, ticktext_hover = _bin_axis_and_hover_labels(nbins)

    if not clamped:
        fig = go.Figure()
        fig.update_layout(
            height=_CHART_HEIGHT_PX,
            margin=dict(l=40, r=16, t=20, b=_X_AXIS_BOTTOM_MARGIN),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(254,242,242,0.55)",
            xaxis=dict(
                title=dict(text=""),
                range=[-0.05, 1.05],
                showgrid=True,
                showticklabels=True,
                tickmode="array",
                tickvals=centers,
                ticktext=ticktext_axis,
                tickangle=0,
                gridcolor="rgba(220,38,38,0.12)",
                zeroline=False,
            ),
            yaxis=dict(
                title="Anzahl Alben",
                showgrid=True,
                gridcolor="rgba(220,38,38,0.08)",
                zeroline=False,
            ),
        )
        return fig

    counts = _bin_counts(clamped, nbins)
    colours = _bar_colours_by_score_position(nbins)
    mean_x = float(statistics.mean(clamped))

    widths = [1.0 / nbins * 0.82] * nbins

    fig = go.Figure(
        data=[
            go.Bar(
                x=centers,
                y=counts,
                width=widths,
                marker=dict(
                    color=colours,
                    line=dict(color="rgba(185,28,28,0.45)", width=1),
                    cornerradius=4,
                ),
                hovertemplate=("Bereich: %{customdata}<br>Anzahl: %{y}<extra></extra>"),
                customdata=ticktext_hover,
            ),
        ],
    )

    fig.update_layout(
        height=_CHART_HEIGHT_PX,
        margin=dict(l=44, r=20, t=20, b=_X_AXIS_BOTTOM_MARGIN),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(254,242,242,0.55)",
        bargap=0.08,
        showlegend=False,
        xaxis=dict(
            title=dict(text=""),
            range=[-0.05, 1.05],
            showticklabels=True,
            tickmode="array",
            tickvals=centers,
            ticktext=ticktext_axis,
            tickangle=0,
            showgrid=True,
            gridcolor="rgba(220,38,38,0.12)",
            zeroline=False,
        ),
        yaxis=dict(
            title="Anzahl Alben",
            rangemode="tozero",
            showgrid=True,
            gridcolor="rgba(220,38,38,0.08)",
            zeroline=False,
        ),
    )

    fig.add_vline(
        x=mean_x,
        line=dict(color=_VLINE_COLOR, width=2, dash="dash"),
        annotation_text="Mittel",
        annotation_position="top",
        annotation=dict(
            font=dict(size=11, color=_VLINE_COLOR),
            bgcolor="rgba(255,255,255,0.85)",
            borderpad=4,
        ),
    )
    return fig


def newest_batch_score_chart_config() -> dict[str, Any]:
    """Streamlit plotly_chart config (no mode bar)."""
    return {"displayModeBar": False}
