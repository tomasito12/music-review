"""Shared data-loading and formatting helpers for Streamlit pages."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from music_review.config import resolve_data_path
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    build_profile_payload,
    default_profiles_dir,
    save_profile,
)
from music_review.io.jsonl import iter_jsonl_objects
from music_review.pipeline.retrieval.reference_graph import load_artist_communities


@st.cache_data(ttl=3600)
def load_communities_res_10() -> list[dict[str, Any]]:
    """Load resolution-10 communities with top artists."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "communities_res_10.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    comms = data.get("communities")
    if not isinstance(comms, list):
        return []
    return [c for c in comms if isinstance(c, dict) and c.get("id")]


@st.cache_data(ttl=3600)
def load_genre_labels_res_10() -> dict[str, str]:
    """Load LLM-assigned genre labels for communities (res_10)."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "community_genre_labels_res_10.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    labels = data.get("labels")
    if not isinstance(labels, list):
        return {}
    mapping: dict[str, str] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        label = item.get("genre_label")
        if cid is None or not label:
            continue
        mapping[str(cid)] = str(label)
    return mapping


@st.cache_data(ttl=3600)
def load_broad_categories_res_10() -> tuple[list[str], dict[str, list[str]]]:
    """Load broad categories and per-community mappings.

    Returns (category names, community_id -> [broad_category, ...]).
    """
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "community_broad_categories_res_10.json"
    if not path.exists():
        return [], {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], {}
    cats = data.get("broad_categories")
    if not isinstance(cats, list):
        cats = []
    cats = [str(c) for c in cats if isinstance(c, str)]
    raw_mappings = data.get("mappings")
    if not isinstance(raw_mappings, list):
        return cats, {}
    mapping: dict[str, list[str]] = {}
    for item in raw_mappings:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        bc = item.get("broad_categories")
        if isinstance(cid, str) and isinstance(bc, list):
            mapping[cid] = [str(c) for c in bc]
    return cats, mapping


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


# Voreinstellung Rating-Filter (Finetuning / fehlende filter_settings).
DEFAULT_PLATTENTESTS_RATING_FILTER_MIN = 7
DEFAULT_PLATTENTESTS_RATING_FILTER_MAX = 10

# Wenn reviews.jsonl fehlt oder kein Jahr enthalten: Untergrenze Jahr-Slider.
YEAR_SLIDER_FALLBACK_FLOOR = 1990


def clamp_plattentests_rating_filter_range(
    rating_min: Any,
    rating_max: Any,
) -> tuple[int, int]:
    """Coerce Plattentests rating filter bounds to whole numbers from 0 to 10.

    Legacy session values may be floats; values are rounded, clamped to the
    scale, and swapped if min exceeded max. Ungültige Eingaben fallen auf
    die übliche UI-Voreinstellung (7-10) zurück.
    """
    try:
        lo = round(float(rating_min))
    except (TypeError, ValueError):
        lo = DEFAULT_PLATTENTESTS_RATING_FILTER_MIN
    try:
        hi = round(float(rating_max))
    except (TypeError, ValueError):
        hi = DEFAULT_PLATTENTESTS_RATING_FILTER_MAX
    lo = max(0, min(10, lo))
    hi = max(0, min(10, hi))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def review_raw_release_year(raw: Mapping[str, Any]) -> int | None:
    """Best release year from one reviews.jsonl row (year field or ISO date)."""
    ry = raw.get("release_year")
    if ry is not None:
        try:
            y = int(ry)
        except (TypeError, ValueError):
            pass
        else:
            if 1800 <= y <= 2100:
                return y
    rd = raw.get("release_date")
    if isinstance(rd, str) and len(rd) >= 4:
        try:
            y = int(rd[:4])
        except ValueError:
            return None
        if 1800 <= y <= 2100:
            return y
    return None


def max_release_year_in_jsonl(path: Path) -> int | None:
    """Scan a reviews JSONL file for the largest release year found."""
    if not path.exists():
        return None
    y_max: int | None = None
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        y = review_raw_release_year(obj)
        if y is None:
            continue
        if y_max is None or y > y_max:
            y_max = y
    return y_max


def min_release_year_in_jsonl(path: Path) -> int | None:
    """Scan a reviews JSONL file for the smallest release year found."""
    if not path.exists():
        return None
    y_min: int | None = None
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        y = review_raw_release_year(obj)
        if y is None:
            continue
        if y_min is None or y < y_min:
            y_min = y
    return y_min


@st.cache_data(ttl=3600)
def max_release_year_from_corpus() -> int:
    """Upper bound for year sliders: max year in data/reviews.jsonl or this year."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "reviews.jsonl"
    m = max_release_year_in_jsonl(path)
    if m is None:
        return datetime.now().year
    return m


@st.cache_data(ttl=3600)
def min_release_year_from_corpus() -> int:
    """Lower bound for year sliders: min year in data/reviews.jsonl or fallback."""
    data_dir = resolve_data_path("data")
    path = Path(data_dir) / "reviews.jsonl"
    m = min_release_year_in_jsonl(path)
    if m is None:
        return YEAR_SLIDER_FALLBACK_FLOOR
    return m


def clamp_year_filter_bounds(
    year_min: Any,
    year_max: Any,
    *,
    year_cap: int,
    year_floor: int = 1990,
) -> tuple[int, int]:
    """Clamp stored year range to [year_floor, year_cap] and ensure min <= max."""
    try:
        lo = int(year_min)
    except (TypeError, ValueError):
        lo = year_floor
    try:
        hi = int(year_max)
    except (TypeError, ValueError):
        hi = year_cap
    lo = max(year_floor, min(lo, year_cap))
    hi = max(year_floor, min(hi, year_cap))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


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


# Discrete Stil-Präferenz (community_spectrum_crossover): UI ohne Zahlen, Wert 0..1.
SPECTRUM_CROSSOVER_STOPS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)

_SPECTRUM_CROSSOVER_LABELS: tuple[str, ...] = (
    "Starker Stil-Fokus",
    "Eher Fokus",
    "Ausgewogen",
    "Eher Breite",
    "Breite Abdeckung",
)


def snap_spectrum_crossover(raw: Any) -> float:
    """Snap any stored crossover (0..1) to the nearest discrete UI stop."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = 0.5
    v = max(0.0, min(1.0, v))
    best = min(SPECTRUM_CROSSOVER_STOPS, key=lambda t: abs(t - v))
    return float(best)


def spectrum_crossover_option_label(stop: float) -> str:
    """German label for one UI stop (``select_slider`` ``format_func``)."""
    idx = SPECTRUM_CROSSOVER_STOPS.index(stop)
    return _SPECTRUM_CROSSOVER_LABELS[idx]


def spectrum_crossover_semantic_label(value: Any) -> str:
    """German label for summaries (e.g. filter recap on the recommendations page)."""
    return spectrum_crossover_option_label(snap_spectrum_crossover(value))


def overall_weights_display_percents(
    style_share: float,
    rating_share: float,
    spectrum_share: float,
) -> tuple[int, int, int]:
    """Integer percentages for Stil-Nähe, Rating, Stil-Präferenz (sum 100).

    Uses largest-remainder so the three values add up to exactly 100.
    """
    a = max(0.0, float(style_share))
    b = max(0.0, float(rating_share))
    c = max(0.0, float(spectrum_share))
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


# Stil-Nähe hell, Rating mittel, Stil-Präferenz im Score dunkel (Balken + Legende).
OVERALL_WEIGHT_TRADEOFF_RED_LIGHT = "#fca5a5"
OVERALL_WEIGHT_TRADEOFF_RED_MID = "#dc2626"
OVERALL_WEIGHT_TRADEOFF_RED_DARK = "#7f1d1d"


def overall_weights_tradeoff_bar_html(
    style_share: float,
    rating_share: float,
    spectrum_share: float,
) -> str:
    """Horizontal stacked bar for normalized overall-score weights (Finetuning)."""
    pa, pb, pg = overall_weights_display_percents(
        style_share,
        rating_share,
        spectrum_share,
    )
    label = f"Stil-Nähe {pa} %, Rating {pb} %, Stil-Präferenz (im Score) {pg} %"
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
        f"Stil-Präferenz (Score) {pg} %</span>"
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


def recommendation_card_meta_parts(
    release_date: Any,
    year: Any,
    rating: float | None,
    overall: float,
    labels: str,
    *,
    default_rating: float = 5.0,
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
    parts.append(f"Score {overall:.2f}")
    if labels:
        parts.append(labels)
    return parts


def recommendation_card_community_tags_html(
    top_comms: list[dict[str, Any]],
) -> str:
    """Build genre-tag pill HTML for a recommendation card (red tones)."""
    import html as _html

    out = '<div class="rec-communities">'
    for tc in top_comms:
        label = str(tc.get("label") or "")
        aff = float(tc.get("affinity") or 0.0)
        bg, border, fg = RECOMMENDATION_CARD_TAG_COLORS[-1][1:]
        for threshold, t_bg, t_border, t_fg in RECOMMENDATION_CARD_TAG_COLORS:
            if aff >= threshold:
                bg, border, fg = t_bg, t_border, t_fg
                break
        out += (
            f'<span class="rec-comm-tag" '
            f'style="background-color:{bg};border-color:{border};'
            f'color:{fg};">'
            f"{_html.escape(label)}</span>"
        )
    out += "</div>"
    return out


_FILTER_EXPANDER_VSPACE_GAPS = frozenset({"sm", "md", "lg", "xl"})


def normalize_filter_expander_vspace_gap(gap: str) -> str:
    """Return a valid spacer size key for Finetuning expander vertical gaps."""
    return gap if gap in _FILTER_EXPANDER_VSPACE_GAPS else "md"


def get_selected_communities() -> set[str]:
    """Return the set of selected community IDs.

    Reads the canonical ``selected_communities`` key first; falls back
    to the legacy union of artist + genre flow keys for backward
    compatibility with old profiles.
    """
    primary = st.session_state.get("selected_communities")
    if isinstance(primary, set) and primary:
        return {str(c) for c in primary}
    artist_comms = st.session_state.get("artist_flow_selected_communities") or set()
    genre_comms = st.session_state.get("genre_flow_selected_communities") or set()
    return {str(c) for c in artist_comms} | {str(c) for c in genre_comms}


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


@st.cache_data(ttl=3600)
def load_community_memberships() -> dict[str, dict[str, str]]:
    """Load artist key (normalized) -> resolution keys -> community id."""
    mp = resolve_data_path("data/community_memberships.jsonl")
    return load_artist_communities(mp)


def save_current_profile_to_disk() -> None:
    """Persist current session settings under the active profile slug."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not active:
        st.warning("Kein Profil aktiv -- bitte zuerst anmelden.")
        return
    profiles_dir = default_profiles_dir()
    selected = get_selected_communities()
    fs = st.session_state.get("filter_settings")
    if not isinstance(fs, dict):
        fs = {}
    weights = st.session_state.get("community_weights_raw")
    if not isinstance(weights, dict):
        weights = {}
    payload = build_profile_payload(
        profile_slug=active,
        flow_mode=st.session_state.get("flow_mode"),
        selected_communities=selected,
        filter_settings=fs,
        community_weights_raw=weights,
    )
    save_profile(profiles_dir, active, payload)
    st.success(f"Profil '{active}' gespeichert.")


def _reset_filters() -> None:
    """Clear all filter/community selections back to defaults."""
    st.session_state["selected_communities"] = set()
    st.session_state["selected_broad_categories"] = set()
    st.session_state["artist_flow_selected_communities"] = set()
    st.session_state["genre_flow_selected_communities"] = set()
    st.session_state["filter_settings"] = {}
    st.session_state["community_weights_raw"] = {}
    st.session_state["free_text_query"] = ""


def render_toolbar(page_key: str) -> None:
    """Compact profile/action bar at the top of every flow page."""
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)

    if active:
        cols = st.columns([2, 1, 1, 1])
        with cols[0]:
            st.caption(f"Angemeldet als **{active}**")
        with cols[1]:
            if st.button("Speichern", key=f"tb_{page_key}_save"):
                save_current_profile_to_disk()
        with cols[2]:
            if st.button("Reset", key=f"tb_{page_key}_reset"):
                _reset_filters()
                st.rerun()
        with cols[3]:
            if st.button("Abmelden", key=f"tb_{page_key}_logout"):
                st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
                st.rerun()
    else:
        col_status, col_login = st.columns([5, 1])
        with col_status:
            st.caption("Kein Profil aktiv")
        with col_login:
            if st.button(
                "Anmelden",
                key=f"tb_{page_key}_login",
                use_container_width=True,
            ):
                st.switch_page("pages/0_Profil.py")

    st.markdown("---")
