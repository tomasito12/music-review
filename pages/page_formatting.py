"""Display formatting helpers for Streamlit recommendation pages."""

from __future__ import annotations

import html as _html
import math
from collections.abc import Collection
from datetime import datetime
from typing import Any

from pages.page_css import (
    OVERALL_WEIGHT_TRADEOFF_RED_DARK,
    OVERALL_WEIGHT_TRADEOFF_RED_LIGHT,
    OVERALL_WEIGHT_TRADEOFF_RED_MID,
)


def community_display_label(
    community_id: str,
    genre_labels: dict[str, str],
    community: dict[str, Any] | None = None,
) -> str:
    """Human-readable name for a music cluster in the UI (never the internal id)."""
    gl = genre_labels.get(community_id)
    if gl:
        return gl
    if isinstance(community, dict):
        centroid = community.get("centroid")
        if centroid:
            return str(centroid)
    return "Stil-Cluster"


def format_style_weight_example_artists(
    top_artists: list[Any] | None,
    *,
    max_chars: int = 55,
) -> str:
    """Example artists for Finetuning cards, aligned with feine Auswahl (up to three).

    Uses the same slice depth as ``build_community_broad_category_index`` (first
    three ``top_artists`` strings). Prefix is ``z. B. ``. Prefer three names; if
    ``len(caption) > max_chars``, use two; if still too long, use one.
    """
    prefix = "z. B. "
    if not top_artists or not isinstance(top_artists, list):
        return ""
    names = [str(a).strip() for a in top_artists if str(a).strip()]
    if not names:
        return ""
    pool = names[:3]
    for n in (3, 2, 1):
        chunk = pool[:n]
        if not chunk:
            continue
        out = prefix + ", ".join(chunk)
        if len(out) <= max_chars or n == 1:
            return out
    return ""


def build_community_broad_category_index(
    communities: list[dict[str, Any]],
    genre_labels: dict[str, str],
    category_mappings: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Group style rows by broad category for the feine Auswahl page.

    Each value entry has ``id``, ``genre_label`` (display), and ``top_artists``
    (up to three strings). Rows without a broad-category mapping go under
    ``Sonstige``.
    """
    index: dict[str, list[dict[str, Any]]] = {}
    for comm in communities:
        cid = str(comm.get("id", ""))
        if not cid:
            continue
        genre_label = community_display_label(cid, genre_labels, comm)
        top_artists = comm.get("top_artists") or []
        if not isinstance(top_artists, list):
            top_artists = []
        cats = category_mappings.get(cid, [])
        info = {
            "id": cid,
            "genre_label": genre_label,
            "top_artists": [str(a) for a in top_artists[:3]],
        }
        if not cats:
            cats = ["Sonstige"]
        for cat in cats:
            index.setdefault(cat, []).append(info)
    for items in index.values():
        items.sort(key=lambda x: str(x["genre_label"]).lower())
    return index


# Schrittweite für den Passungs-Slider in Prozent (entspricht 0.05 im 0-1-Score).
STYLE_MATCH_FILTER_PERCENT_STEP = 5


def style_match_percent_tuple_for_slider(
    score_min: Any,
    score_max: Any,
    *,
    step: int = STYLE_MATCH_FILTER_PERCENT_STEP,
) -> tuple[int, int]:
    """Wandelt gespeicherte Scores (0..1) in Prozent 0..100 für den Slider.

    Werte werden auf *step* gerundet (wie im Finetuning-Slider). Reihenfolge
    wird so normalisiert, dass die linke Marke die untere Grenze ist.
    """
    try:
        lo_f = float(score_min)
    except (TypeError, ValueError):
        lo_f = 0.0
    try:
        hi_f = float(score_max)
    except (TypeError, ValueError):
        hi_f = 1.0
    lo_f = max(0.0, min(1.0, lo_f))
    hi_f = max(0.0, min(1.0, hi_f))
    lo = max(0, min(100, round(lo_f * 100)))
    hi = max(0, min(100, round(hi_f * 100)))
    if lo > hi:
        lo, hi = hi, lo
    if step > 0:
        lo = max(0, min(100, round(lo / step) * step))
        hi = max(0, min(100, round(hi / step) * step))
        if lo > hi:
            lo, hi = hi, lo
    return lo, hi


def style_match_scores_from_percent_slider(
    lo_pct: int,
    hi_pct: int,
) -> tuple[float, float]:
    """Mappt Prozent-Slider-Werte zurück auf score_min/score_max (0..1)."""
    lo = max(0, min(100, int(lo_pct)))
    hi = max(0, min(100, int(hi_pct)))
    if lo > hi:
        lo, hi = hi, lo
    return lo / 100.0, hi / 100.0


def format_style_match_range_display(score_min: Any, score_max: Any) -> str:
    """Kurztext für Zusammenfassungen, z.B. ``45 % bis 100 %`` (intern 0..1)."""
    try:
        lo = round(float(score_min) * 100)
    except (TypeError, ValueError):
        lo = 0
    try:
        hi = round(float(score_max) * 100)
    except (TypeError, ValueError):
        hi = 100
    lo = max(0, min(100, lo))
    hi = max(0, min(100, hi))
    if lo > hi:
        lo, hi = hi, lo
    return f"{lo} % bis {hi} %"


def overall_weights_display_percents(
    style_share: float,
    rating_share: float,
    breadth_share: float,
) -> tuple[int, int, int]:
    """Integer percentages for Stilpassung, Rating, Stilbreite (sum 100)."""
    a = max(0.0, float(style_share))
    b = max(0.0, float(rating_share))
    c = max(0.0, float(breadth_share))
    s = a + b + c
    if s <= 0.0:
        return (34, 33, 33)
    parts = (a / s, b / s, c / s)
    scaled = [p * 100.0 for p in parts]
    floors = [math.floor(x) for x in scaled]
    rem = 100 - sum(floors)
    fracs = sorted(
        ((scaled[i] - floors[i], i) for i in range(3)),
        key=lambda t: t[0],
        reverse=True,
    )
    out = list(floors)
    for k in range(rem):
        out[fracs[k][1]] += 1
    return (int(out[0]), int(out[1]), int(out[2]))


def overall_weights_tradeoff_bar_html(
    style_share: float,
    rating_share: float,
    breadth_share: float,
) -> str:
    """Horizontal stacked bar for normalized overall-score weights (Finetuning)."""
    pa, pb, pg = overall_weights_display_percents(
        style_share,
        rating_share,
        breadth_share,
    )
    label = f"Stil-Nähe {pa} %, Rating {pb} %, Stilbreite {pg} %"
    rl, rm, rd = (
        OVERALL_WEIGHT_TRADEOFF_RED_LIGHT,
        OVERALL_WEIGHT_TRADEOFF_RED_MID,
        OVERALL_WEIGHT_TRADEOFF_RED_DARK,
    )
    dot = '<span style="color:#9ca3af;margin:0 0.3rem;">·</span>'
    return (
        '<div class="ow-tradeoff-wrap">'
        '<p class="ow-tradeoff-legend">'
        "<strong>Verteilung im Gesamtscore:</strong> "
        f'<span style="color:{rl};font-weight:600;">Stil-Nähe {pa} %</span>'
        f"{dot}"
        f'<span style="color:{rm};font-weight:600;">Rating {pb} %</span>'
        f"{dot}"
        f'<span style="color:{rd};font-weight:600;">'
        f"Stilbreite {pg} %</span>"
        "</p>"
        f'<div class="ow-tradeoff-bar" role="img" aria-label="{label}">'
        f'<span class="ow-tradeoff-seg" style="width:{pa}%;background:{rl};"></span>'
        f'<span class="ow-tradeoff-seg" style="width:{pb}%;background:{rm};"></span>'
        f'<span class="ow-tradeoff-seg" style="width:{pg}%;background:{rd};"></span>'
        "</div></div>"
    )


RECOMMENDATION_CARD_TAG_COLORS: tuple[tuple[float, str, str, str], ...] = (
    (0.6, "#7f1d1d", "#7f1d1d", "#fef2f2"),
    (0.3, "#dc2626", "#b91c1c", "#fff1f2"),
    (0.1, "#fecaca", "#fca5a5", "#1f2937"),
    (0.0, "#f3f4f6", "#e5e7eb", "#4b5563"),
)


def format_record_labels_for_card(
    metadata_labels: Any,
    review_labels: list[str] | None,
) -> str:
    """Build comma-separated Plattenlabel text for recommendation cards.

    Uses labels from imputed/metadata JSONL when present; otherwise the
    label list scraped with the review (plattentests). Chroma hit metadata
    may pass a single pre-joined string instead of a list.
    """
    if isinstance(metadata_labels, str):
        s = metadata_labels.strip()
        if s:
            return s
    items: list[str] = []
    if isinstance(metadata_labels, list):
        items = [str(x).strip() for x in metadata_labels if str(x).strip()]
        if items:
            return ", ".join(items)
    if review_labels:
        items = [str(x).strip() for x in review_labels if str(x).strip()]
        return ", ".join(items)
    return ""


def recommendation_card_meta_parts(
    release_date: Any,
    year: Any,
    rating: float | None,
    overall: float,
    labels: str,
    *,
    default_rating: float = 5.0,
    include_overall_score: bool = True,
) -> list[str]:
    """Build simplified meta-line segments for a recommendation card."""
    parts: list[str] = []
    release_str = format_release_date(release_date, year)
    if release_str:
        parts.append(release_str)
    if rating is not None:
        parts.append(f"Rating {float(rating):g}/10")
    else:
        parts.append(f"Rating {default_rating:.0f}/10 (angenommen)")
    if include_overall_score:
        parts.append(f"Score {overall:.2f}")
    label_plain = labels.strip()
    if label_plain:
        parts.append(f"Plattenlabel: {label_plain}")
    return parts


def recommendation_card_community_tags_html(
    top_comms: list[dict[str, Any]],
    *,
    filter_selected_community_ids: Collection[str] | None = None,
) -> str:
    """Build genre-tag pill HTML for a recommendation card (red tones).

    Tags whose community ``id`` is in ``filter_selected_community_ids`` get a
    a soft black double ring (class ``rec-comm-tag--filtered``); affinity
    colours on the pill stay unchanged.
    """

    def _normalize_comm_id(raw: Any) -> str:
        """Normalize community IDs for robust matching across cases/whitespace."""
        return str(raw).strip().casefold()

    highlight: set[str] | None = None
    if filter_selected_community_ids:
        highlight = {_normalize_comm_id(x) for x in filter_selected_community_ids}

    out = '<div class="rec-communities">'
    for tc in top_comms:
        label = str(tc.get("label") or "")
        aff = float(tc.get("affinity") or 0.0)
        cid_raw = tc.get("id")
        cid = _normalize_comm_id(cid_raw) if cid_raw is not None else ""
        bg, border, fg = RECOMMENDATION_CARD_TAG_COLORS[-1][1:]
        for threshold, t_bg, t_border, t_fg in RECOMMENDATION_CARD_TAG_COLORS:
            if aff >= threshold:
                bg, border, fg = t_bg, t_border, t_fg
                break
        filtered_cls = (
            " rec-comm-tag--filtered"
            if highlight is not None and cid and cid in highlight
            else ""
        )
        out += (
            f'<span class="rec-comm-tag{filtered_cls}" '
            f'style="background-color:{bg};border-color:{border};'
            f'color:{fg};">'
            f"{_html.escape(label)}</span>"
        )
    out += "</div>"
    return out


def release_year_for_card_meta(review: Any) -> int | None:
    """Calendar year for recommendation-style meta (``release_year`` or date)."""
    ry = getattr(review, "release_year", None)
    if ry is not None:
        try:
            return int(ry)
        except (TypeError, ValueError):
            pass
    rd = getattr(review, "release_date", None)
    if rd is not None and hasattr(rd, "year"):
        try:
            return int(rd.year)
        except (TypeError, ValueError):
            pass
    return None


def format_release_date(value: Any, release_year: Any) -> str:
    """Format release date for display cards.

    Supports datetime/date objects and ISO date strings.
    """
    if value is not None:
        if hasattr(value, "strftime"):
            try:
                return value.strftime("%d.%m.%Y")
            except Exception:
                pass
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime("%d.%m.%Y")
            except ValueError:
                pass
    if release_year is not None:
        try:
            return str(int(release_year))
        except (TypeError, ValueError):
            pass
    return ""
