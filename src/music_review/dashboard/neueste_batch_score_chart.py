"""Plotly chart and caption for newest-album batch score distribution (Streamlit UI)."""

from __future__ import annotations

import statistics
from typing import Any

import plotly.graph_objects as go

SCORE_HIST_NUM_BINS = 8

# Caption thresholds (share of albums with score >= 0.5, and median).
_CAPTION_HIGH_SHARE = 0.55
_CAPTION_LOW_SHARE = 0.38
_CAPTION_HIGH_MEDIAN = 0.48
_CAPTION_LOW_MEDIAN = 0.42

# Bar colours (light rose to deep red by relative height).
_COLOR_LIGHT = "#fecaca"
_COLOR_MID = "#f87171"
_COLOR_DEEP = "#b91c1c"

_CHART_HEIGHT_PX = 190
_VLINE_COLOR = "#991b1b"


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


def _bar_colours(counts: list[int]) -> list[str]:
    if not counts:
        return []
    peak = max(counts)
    if peak <= 0:
        return [_COLOR_LIGHT for _ in counts]
    out: list[str] = []
    for c in counts:
        t = c / peak
        if t < 0.34:
            out.append(_COLOR_LIGHT)
        elif t < 0.67:
            out.append(_COLOR_MID)
        else:
            out.append(_COLOR_DEEP)
    return out


def _bin_centers(nbins: int) -> list[float]:
    w = 1.0 / nbins
    return [w * (i + 0.5) for i in range(nbins)]


def _bin_ticktexts(nbins: int) -> list[str]:
    """German decimal comma, short range labels per bin."""
    w = 1.0 / nbins
    texts: list[str] = []
    for i in range(nbins):
        a = i * w
        b = (i + 1) * w if i < nbins - 1 else 1.0
        texts.append(
            f"{a:.2f}".replace(".", ",") + " - " + f"{b:.2f}".replace(".", ","),
        )
    return texts


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
    if share <= _CAPTION_LOW_SHARE or med < _CAPTION_LOW_MEDIAN:
        return (
            "In diesem Ausschnitt liegen die neuesten Alben überwiegend weiter weg von "
            "deinem Profil (eher durchmischt)."
        )
    return (
        "In diesem Ausschnitt mischt sich Passendes mit weniger Passendem — ein "
        "typischer Querschnitt der neuesten Alben zu deinem Profil."
    )


def build_newest_batch_score_figure(scores: list[float]) -> go.Figure:
    """Bar histogram on [0, 1] with mean vline and rose/red styling."""
    clamped = _clamp_unit_interval(scores)
    nbins = SCORE_HIST_NUM_BINS
    centers = _bin_centers(nbins)
    ticktext = _bin_ticktexts(nbins)

    if not clamped:
        fig = go.Figure()
        fig.update_layout(
            height=_CHART_HEIGHT_PX,
            margin=dict(l=40, r=16, t=28, b=48),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(254,242,242,0.55)",
            xaxis=dict(
                title="Passung (Score)",
                range=[-0.05, 1.05],
                showgrid=True,
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
    colours = _bar_colours(counts)
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
                customdata=ticktext,
            ),
        ],
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

    fig.update_layout(
        height=_CHART_HEIGHT_PX,
        margin=dict(l=44, r=20, t=32, b=52),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(254,242,242,0.55)",
        bargap=0.08,
        showlegend=False,
        xaxis=dict(
            title="Passung (Score)",
            range=[-0.05, 1.05],
            tickmode="array",
            tickvals=centers,
            ticktext=ticktext,
            tickangle=-35,
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
    return fig


def newest_batch_score_chart_config() -> dict[str, Any]:
    """Streamlit plotly_chart config (no mode bar)."""
    return {"displayModeBar": False}
