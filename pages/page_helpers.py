"""Shared data-loading and formatting helpers for Streamlit pages."""

from __future__ import annotations

import contextlib
import json
import math
from collections.abc import Collection, Mapping, MutableMapping
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from music_review.config import resolve_data_path
from music_review.dashboard.taste_setup import (
    clear_taste_wizard_reset_pending,
    data_implies_taste_setup_complete,
    is_taste_setup_complete,
    mark_taste_wizard_reset_pending,
)
from music_review.dashboard.user_db import (
    create_session_token,
    delete_session_token,
    load_user_profile,
    validate_session_token,
)
from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_COOKIE_NAME,
    ACTIVE_PROFILE_SESSION_KEY,
    ProfileHydrationResult,
    apply_profile_to_session,
    build_profile_payload,
    default_profiles_dir,
    ensure_active_profile_hydrated,
    normalize_profile_slug,
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

# Session-State-Schlüssel für das Plattenlabel-Multiselect auf der Filterseite.
FILTER_PLATTENLABEL_MULTISELECT_KEY = "filter_plattenlabel_multiselect"

# Semantische Freitext-Suche (Expander im Filter-Flow; Treffer auf Empfehlungen).
SEMANTIC_CHAT_RESET_BUTTON_KEY = "rec_chat_reset_button"
SEMANTIC_CHAT_INPUT_KEY = "rec_chat_input"
SEMANTIC_RAG_MAX_DISTANCE_KEY = "rec_rag_max_distance"
SEMANTIC_CHAT_MESSAGES_KEY = "rec_chat_messages"

# Browser cookie for session-token-based login (replaces plain slug cookie).
SESSION_TOKEN_COOKIE_NAME = "mr_session_token"

# Spotify OAuth CSRF state (browser cookie; survives URL navigation / new session).
SPOTIFY_OAUTH_STATE_COOKIE_NAME = "mr_spotify_oauth_state"
# PKCE code_verifier (same lifetime as OAuth state; required for token exchange).
SPOTIFY_PKCE_VERIFIER_COOKIE_NAME = "mr_spotify_pkce_verifier"
# Filter/taste session snapshot before Spotify redirect (survives profile re-hydrate).
SPOTIFY_SESSION_SNAPSHOT_COOKIE_NAME = "mr_spotify_session_snapshot"
# Open Spotify connection UI after "Vorschau erzeugen" without a token (Streamlit).
SPOTIFY_SURFACE_CONNECTION_UI_KEY = "spotify_surface_connection_ui"

# Streamlit widget session keys for Schritt 3 sliders (cleared on taste reset).
FILTER_FLOW_WIDGET_KEY_YEAR_RANGE = "filter_flow_year_range"
FILTER_FLOW_WIDGET_KEY_RATING_RANGE = "filter_flow_rating_range"
FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT = "filter_flow_style_match_pct"
FILTER_FLOW_WIDGET_KEY_SPECTRUM = "filter_flow_spectrum_crossover"
FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA = "filter_flow_overall_alpha"
FILTER_FLOW_WIDGET_KEY_OVERALL_BETA = "filter_flow_overall_beta"
FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA = "filter_flow_overall_gamma"

FILTER_FLOW_WIDGET_KEYS: tuple[str, ...] = (
    FILTER_FLOW_WIDGET_KEY_YEAR_RANGE,
    FILTER_FLOW_WIDGET_KEY_RATING_RANGE,
    FILTER_FLOW_WIDGET_KEY_STYLE_MATCH_PCT,
    FILTER_FLOW_WIDGET_KEY_SPECTRUM,
    FILTER_FLOW_WIDGET_KEY_OVERALL_ALPHA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_BETA,
    FILTER_FLOW_WIDGET_KEY_OVERALL_GAMMA,
)

# Checkbox/slider keys on Schritt 1/2/3 that must be dropped when taste resets.
TASTE_WIZARD_WIDGET_KEY_PREFIXES: tuple[str, ...] = (
    "comm_sel_",
    "broad_cat_",
    "weight_comm_",
)

# Sammel-Option in der Filter-UI für seltene Plattenlabels.
PLATTENLABEL_SONSTIGE_UI = "Sonstige"

# Plattenlabels mit mehr als so vielen Alben erscheinen einzeln in der Filter-UI;
# alle anderen laufen über „Sonstige“ (streng: ``Anzahl Alben >`` dieser Schwelle).
PLATTENLABEL_INDIVIDUAL_LIST_MIN_ALBUMS = 50


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


def unique_plattenlabels_from_reviews_jsonl(path: Path) -> list[str]:
    """Return sorted unique non-empty label strings from a reviews JSONL file."""
    labels: set[str] = set()
    for obj in iter_jsonl_objects(path, log_errors=False):
        raw = obj.get("labels")
        if not isinstance(raw, list):
            continue
        for lab in raw:
            s = str(lab).strip()
            if s:
                labels.add(s)
    return sorted(labels)


def _plattenlabel_row_sets_and_album_index(
    path: Path,
) -> tuple[list[frozenset[str]], dict[str, set[int]], int]:
    """Build per-row label sets and label -> album index sets from reviews JSONL."""
    row_label_sets: list[frozenset[str]] = []
    for obj in iter_jsonl_objects(path, log_errors=False):
        if not isinstance(obj, dict):
            continue
        raw = obj.get("labels")
        seen_in_row: set[str] = set()
        if isinstance(raw, list):
            for lab in raw:
                s = str(lab).strip()
                if s and s not in seen_in_row:
                    seen_in_row.add(s)
        row_label_sets.append(frozenset(seen_in_row))

    n_reviews = len(row_label_sets)
    label_to_album_indices: dict[str, set[int]] = {}
    for i, labs in enumerate(row_label_sets):
        for lab in labs:
            label_to_album_indices.setdefault(lab, set()).add(i)
    return row_label_sets, label_to_album_indices, n_reviews


def plattenlabel_album_count_buckets_from_reviews_jsonl(
    path: Path,
    *,
    min_albums_exclusive: int = PLATTENLABEL_INDIVIDUAL_LIST_MIN_ALBUMS,
) -> tuple[list[str], list[str], int]:
    """Split labels into individual list vs „Sonstige“ by album count.

    Alben = Zeilen in ``reviews.jsonl``. Pro Album werden doppelte
    Label-Strings in einer Zeile nur einmal gezählt (EU/US-Mehrfachlabels).

    Ein Label ist einzeln wählbar, wenn es auf **mehr als**
    ``min_albums_exclusive`` Alben vorkommt. Übrige Labels sind „selten“ und
    werden alphabetisch sortiert für die UI-Logik unter „Sonstige“.

    Rückgabe: ``(frequent_by_count_then_name, rare_sorted_a_z, n_reviews)``.
    """
    _, label_to_album_indices, n_reviews = _plattenlabel_row_sets_and_album_index(
        path,
    )
    if n_reviews == 0:
        return [], [], 0

    if not label_to_album_indices:
        return [], [], n_reviews

    threshold = int(min_albums_exclusive)
    sorted_by_freq = sorted(
        label_to_album_indices.keys(),
        key=lambda lab: (-len(label_to_album_indices[lab]), lab),
    )
    frequent = [
        lab for lab in sorted_by_freq if len(label_to_album_indices[lab]) > threshold
    ]
    frequent_set = frozenset(frequent)
    rare = sorted(lab for lab in label_to_album_indices if lab not in frequent_set)
    return frequent, rare, n_reviews


@st.cache_data(ttl=3600)
def load_plattenlabel_filter_buckets() -> tuple[list[str], list[str], int]:
    """Cached head/tail Plattenlabel buckets from ``data/reviews.jsonl``."""
    p = Path(resolve_data_path("data/reviews.jsonl"))
    return plattenlabel_album_count_buckets_from_reviews_jsonl(p)


def expand_plattenlabel_ui_selection(
    ui: list[str],
    rare: list[str],
    *,
    sonstige_token: str = PLATTENLABEL_SONSTIGE_UI,
) -> list[str]:
    """Turn multiselect values into concrete labels (expand „Sonstige“)."""
    picked = {str(x).strip() for x in ui if str(x).strip()}
    if sonstige_token in picked:
        picked.discard(sonstige_token)
        picked.update(str(r).strip() for r in rare if str(r).strip())
    return sorted(picked)


def collapse_plattenlabel_ui_selection(
    concrete: set[str],
    frequent: list[str],
    rare: list[str],
    *,
    sonstige_token: str = PLATTENLABEL_SONSTIGE_UI,
) -> list[str]:
    """Build multiselect values from stored concrete label set."""
    rare_set = frozenset(str(r).strip() for r in rare if str(r).strip())
    ui: list[str] = [f for f in frequent if f in concrete]
    if rare_set and rare_set <= concrete:
        ui.append(sonstige_token)
    return ui


@st.cache_data(ttl=3600)
def load_sorted_unique_plattenlabels_from_reviews() -> list[str]:
    """Load sorted unique Plattenlabels from ``data/reviews.jsonl`` (cached)."""
    p = Path(resolve_data_path("data/reviews.jsonl"))
    return unique_plattenlabels_from_reviews_jsonl(p)


def plattenlabel_filter_passes(
    album_labels: list[str] | None,
    selection: Any,
    all_labels: list[str],
) -> bool:
    """Whether an album passes the Plattenlabel expert filter.

    - Missing or invalid ``selection`` (e.g. old profiles): no filtering.
    - When the selection equals the full corpus set: no filtering.
    - When the selection is empty: only albums without labels pass.
    - Otherwise: pass if the album has no labels or shares at least one
      label with the selection (OR across the album's labels).
    """
    if not all_labels:
        return True
    all_set = frozenset(str(x).strip() for x in all_labels if str(x).strip())
    if selection is None:
        return True
    if not isinstance(selection, list):
        return True
    sel_set = frozenset(str(x).strip() for x in selection if str(x).strip())
    if sel_set == all_set:
        return True
    raw_album = list(album_labels) if album_labels else []
    album_set = frozenset(str(x).strip() for x in raw_album if str(x).strip())
    if not sel_set:
        return len(album_set) == 0
    if not album_set:
        return True
    return bool(album_set & sel_set)


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
    import html as _html

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


_REC_FLOW_SHELL_CHAT_AVATAR_CSS = """
        div[data-testid="chatAvatarIcon-assistant"] {
            background-color: #fef2f2 !important;
            color: #991b1b !important;
        }
"""

# Assistant-Avatar im Finetuning-Expander „Semantische Suche“ (Filter-Flow).
SEMANTIC_SEARCH_CHAT_AVATAR_CSS = _REC_FLOW_SHELL_CHAT_AVATAR_CSS.strip()

# Shared by Empfehlungen (6) and Neueste Rezensionen (8); keep in sync visually.
_RECOMMENDATION_FLOW_SHELL_CSS_BASE = """
        .rec-hero {
            text-align: center;
            padding: 0.5rem 0 0.15rem 0;
        }
        .rec-page-title {
            font-size: 1.6rem;
            font-weight: 650;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        div[data-testid="stMarkdownContainer"] #rec-page-desc-wrap {
            text-align: center !important;
            width: 100% !important;
            box-sizing: border-box;
            margin: 0 0 1.3rem 0 !important;
        }
        div[data-testid="stMarkdownContainer"] #rec-page-desc-wrap .rec-page-desc {
            color: #6b7280;
            font-size: 0.9rem;
            max-width: 34rem;
            margin: 0 auto !important;
            text-align: center !important;
            line-height: 1.55;
        }
        .rec-sort-section-label {
            font-size: 0.92rem;
            font-weight: 650;
            color: #111827;
            margin-bottom: 0.55rem;
        }
        .rec-card {
            background: #fafafa;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .rec-card:hover {
            border-color: #fca5a5;
            box-shadow: 0 4px 8px rgba(220, 38, 38, 0.08);
        }
        .rec-card-rag {
            border: 1px solid #fca5a5;
            background: #fef2f2;
        }
        .rec-header {
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            flex-wrap: wrap;
        }
        a.rec-title,
        a.rec-title:link,
        a.rec-title:visited,
        div[data-testid="stMarkdownContainer"] a.rec-title {
            font-size: 1.08rem;
            font-weight: 600;
            text-decoration: none;
            color: #1f2937 !important;
            letter-spacing: -0.01em;
        }
        a.rec-title:hover,
        div[data-testid="stMarkdownContainer"] a.rec-title:hover {
            text-decoration: underline;
            color: #dc2626 !important;
        }
        a.rec-title:active,
        div[data-testid="stMarkdownContainer"] a.rec-title:active {
            color: #991b1b !important;
        }
        .rec-meta {
            font-size: 0.8rem;
            color: #6b7280;
            margin-bottom: 0.40rem;
        }
        .rec-communities {
            font-size: 0.78rem;
            color: #4b5563;
            margin-bottom: 0.35rem;
        }
        .rec-comm-tag {
            display: inline-flex;
            align-items: center;
            padding: 0.10rem 0.45rem;
            margin: 0 0.25rem 0.25rem 0;
            border-radius: 999px;
            border: 1px solid transparent;
            font-size: 0.78rem;
            white-space: nowrap;
        }
        .rec-comm-tag.rec-comm-tag--filtered {
            box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.22),
                0 0 0 3px rgba(0, 0, 0, 0.06);
        }
        .rec-excerpt {
            font-size: 0.86rem;
            line-height: 1.5;
            color: #4b5563;
        }
        .rec-rank {
            font-variant-numeric: tabular-nums;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 1.8rem;
            height: 1.45rem;
            padding: 0 0.4rem;
            border-radius: 6px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 0.55rem;
            flex-shrink: 0;
        }
        .rec-pane-header {
            margin: -0.15rem 0 0.85rem 0;
            padding: 0.2rem 0 0.85rem 0.85rem;
            border-bottom: 1px solid rgba(220, 38, 38, 0.2);
        }
        .rec-pane-header-filter {
            border-left: 3px solid #dc2626;
        }
        .rec-pane-header-semantic {
            border-left: 3px solid #7f1d1d;
            border-bottom-color: rgba(127, 29, 29, 0.2);
        }
        .rec-eyebrow {
            font-size: 0.65rem;
            font-weight: 650;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.28rem;
        }
        .rec-pane-header-semantic .rec-eyebrow {
            color: #991b1b;
        }
        .rec-pane-title {
            font-size: 1.02rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #0f172a;
            line-height: 1.3;
        }
        .rec-pane-sub {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 0.45rem;
            line-height: 1.45;
        }
        .rec-results-divider {
            margin: 1rem 0 0.65rem 0;
            padding-top: 0.85rem;
            border-top: 1px dashed rgba(220, 38, 38, 0.25);
        }
        .rec-results-label {
            font-size: 0.68rem;
            font-weight: 650;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #dc2626;
            margin-bottom: 0.35rem;
        }
        .rec-results-title {
            font-size: 0.92rem;
            font-weight: 600;
            color: #991b1b;
            letter-spacing: -0.01em;
        }
        .rec-callout {
            font-size: 0.84rem;
            color: #57534e;
            background: #fafaf9;
            border: 1px solid #e7e5e4;
            border-radius: 10px;
            padding: 0.75rem 1rem;
            line-height: 1.5;
            margin: 0.35rem 0 0.5rem 0;
        }
        .rec-callout-warn {
            background: #fff1f2;
            border-color: #fda4af;
            color: #881337;
        }
        .rec-callout-info {
            background: #fef2f2;
            border-color: #fecaca;
            color: #991b1b;
        }
"""


def recommendation_flow_shell_css_rules(
    *,
    include_chat_avatar_style: bool = False,
    extra_rules: str = "",
) -> str:
    """Return CSS rules for the shared recommendation / newest-reviews card shell."""
    parts: list[str] = [_RECOMMENDATION_FLOW_SHELL_CSS_BASE.strip()]
    if include_chat_avatar_style:
        parts.append(_REC_FLOW_SHELL_CHAT_AVATAR_CSS.strip())
    extra = extra_rules.strip()
    if extra:
        parts.append(extra)
    return "\n".join(parts)


def inject_recommendation_flow_shell_css(
    *,
    include_chat_avatar_style: bool = False,
    extra_rules: str = "",
) -> None:
    """Inject shared shell styles into the active Streamlit page."""
    rules = recommendation_flow_shell_css_rules(
        include_chat_avatar_style=include_chat_avatar_style,
        extra_rules=extra_rules,
    )
    st.markdown(f"<style>\n{rules}\n</style>", unsafe_allow_html=True)


_FILTER_EXPANDER_VSPACE_GAPS = frozenset({"sm", "md", "lg", "xl"})


def normalize_filter_expander_vspace_gap(gap: str) -> str:
    """Return a valid spacer size key for Finetuning expander vertical gaps."""
    return gap if gap in _FILTER_EXPANDER_VSPACE_GAPS else "md"


@st.cache_data(ttl=3600)
def search_rag_hits_for_dashboard(
    query_text: str,
    *,
    strategy: str = "B",
    n_results: int = 2500,
    top_k_per_variant: int = 2500,
) -> list[dict[str, Any]]:
    """Run Chroma semantic search for the dashboard free-text field."""
    from music_review.pipeline.retrieval.vector_store import (
        CHUNK_COLLECTION_NAME,
        search_reviews_with_variants,
    )

    return search_reviews_with_variants(
        query_text,
        strategy=strategy,
        n_results=n_results,
        top_k_per_variant=top_k_per_variant,
        where=None,
        collection_name=CHUNK_COLLECTION_NAME,
    )


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


def session_taste_setup_complete() -> bool:
    """True when genre, communities, and filter merge step are done for this session."""
    return is_taste_setup_complete(st.session_state)


def refresh_taste_wizard_after_filter_save() -> None:
    """Clear the post-reset gate once merged filter data satisfies completion rules."""
    if data_implies_taste_setup_complete(st.session_state):
        clear_taste_wizard_reset_pending(st.session_state)


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


@st.cache_data(ttl=3600)
def load_community_memberships() -> dict[str, dict[str, str]]:
    """Load artist key (normalized) -> resolution keys -> community id."""
    mp = resolve_data_path("data/community_memberships.jsonl")
    return load_artist_communities(mp)


def build_session_profile_payload(*, profile_slug: str) -> dict[str, Any]:
    """Assemble profile JSON from the current Streamlit session (taste + filters)."""
    selected = get_selected_communities()
    fs = st.session_state.get("filter_settings")
    if not isinstance(fs, dict):
        fs = {}
    weights = st.session_state.get("community_weights_raw")
    if not isinstance(weights, dict):
        weights = {}
    return build_profile_payload(
        profile_slug=profile_slug,
        flow_mode=st.session_state.get("flow_mode"),
        selected_communities=selected,
        filter_settings=fs,
        community_weights_raw=weights,
    )


def persist_active_profile_from_session() -> str | None:
    """Write taste + filter session to profile JSON when a profile slug is active.

    Returns the normalized slug after a successful write, otherwise ``None``
    (guest / invalid slug).
    """
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        slug = normalize_profile_slug(raw)
    except ValueError:
        return None
    profiles_dir = default_profiles_dir()
    payload = build_session_profile_payload(profile_slug=slug)
    save_profile(profiles_dir, slug, payload)
    return slug


def save_current_profile_to_disk() -> None:
    """Persist current session settings under the active profile slug."""
    slug = persist_active_profile_from_session()
    if slug is None:
        st.warning("Kein Profil aktiv -- bitte zuerst anmelden.")
        return
    st.success(f"Profil '{slug}' gespeichert.")


def _pop_taste_wizard_widget_session_keys(state: MutableMapping[str, Any]) -> None:
    """Remove Streamlit widget keys so checkboxes/sliders re-sync to cleared data.

    Widgets with explicit ``key=`` keep their values in session state even when
    canonical keys like ``selected_communities`` are cleared; unkeyed sliders
    also retain internal state. Dropping these keys forces the next run to use
    defaults derived from empty ``filter_settings`` / selection sets.
    """
    for k in list(state.keys()):
        if not isinstance(k, str):
            continue
        if any(k.startswith(p) for p in TASTE_WIZARD_WIDGET_KEY_PREFIXES):
            state.pop(k, None)
    for k in FILTER_FLOW_WIDGET_KEYS:
        state.pop(k, None)


def _reset_filters() -> None:
    """Clear all filter/community selections back to defaults."""
    st.session_state["selected_communities"] = set()
    st.session_state["selected_broad_categories"] = set()
    st.session_state["artist_flow_selected_communities"] = set()
    st.session_state["genre_flow_selected_communities"] = set()
    st.session_state["filter_settings"] = {}
    st.session_state["community_weights_raw"] = {}
    st.session_state["free_text_query"] = ""
    st.session_state.pop(SEMANTIC_CHAT_MESSAGES_KEY, None)
    st.session_state.pop(SEMANTIC_RAG_MAX_DISTANCE_KEY, None)
    st.session_state.pop(SEMANTIC_CHAT_INPUT_KEY, None)
    st.session_state.pop(FILTER_PLATTENLABEL_MULTISELECT_KEY, None)
    _pop_taste_wizard_widget_session_keys(st.session_state)


def reset_taste_preferences() -> None:
    """Clear taste-related session keys; the user must run the setup wizard again."""
    _reset_filters()
    mark_taste_wizard_reset_pending(st.session_state)
    st.session_state["flow_mode"] = None


def logout_active_profile() -> None:
    """Sign out: invalidate session token, clear cookie, clear taste keys."""
    _invalidate_current_session_token()
    st.session_state.pop(ACTIVE_PROFILE_SESSION_KEY, None)
    clear_session_token_cookie()
    reset_taste_preferences()


# CookieManager uses a fixed element key; only one instance per session.
_PROFILE_COOKIE_MANAGER_STATE_KEY = "_mr_profile_cookie_manager_singleton"


def profile_cookie_manager() -> Any:
    """Shared CookieManager so the component is not instantiated twice in one run."""
    import extra_streamlit_components as stx

    existing = st.session_state.get(_PROFILE_COOKIE_MANAGER_STATE_KEY)
    if existing is not None:
        return existing
    cm = stx.CookieManager(key="mr_profile_cookie_mgr")
    st.session_state[_PROFILE_COOKIE_MANAGER_STATE_KEY] = cm
    return cm


def _safe_cookie_manager_delete(cm: Any, cookie_name: str, *, key: str) -> None:
    """Call CookieManager.delete without failing when the name is absent locally.

    The third-party component runs ``del self.cookies[cookie_name]`` after the
    delete request; that raises :exc:`KeyError` when the cookie was never stored
    in the in-memory dict (e.g.     OAuth callback before ``set`` synced).
    """
    with contextlib.suppress(KeyError):
        cm.delete(cookie_name, key=key)


def persist_session_token_cookie(token: str) -> None:
    """Store a session token in the browser (same-site lax, 30 days)."""
    if not isinstance(token, str) or not token.strip():
        return
    cm = profile_cookie_manager()
    cm.set(
        SESSION_TOKEN_COOKIE_NAME,
        token,
        key="mr_cookie_set_session_token",
        max_age=60.0 * 60 * 24 * 30,
        same_site="lax",
    )


def clear_session_token_cookie() -> None:
    """Remove the session-token cookie (logout or invalid token)."""
    cm = profile_cookie_manager()
    _safe_cookie_manager_delete(
        cm,
        SESSION_TOKEN_COOKIE_NAME,
        key="mr_cookie_del_session_token",
    )
    _safe_cookie_manager_delete(
        cm,
        ACTIVE_PROFILE_COOKIE_NAME,
        key="mr_cookie_del_profile",
    )


def persist_active_profile_slug_cookie(slug: str) -> None:
    """Create a DB session and store its token in the browser cookie.

    This is the main login-persistence entry point used by the profile page
    after successful authentication.
    """
    try:
        safe = normalize_profile_slug(slug)
    except ValueError:
        return
    conn = get_db_connection()
    token = create_session_token(conn, safe)
    persist_session_token_cookie(token)


def clear_active_profile_slug_cookie() -> None:
    """Remove session cookie and invalidate DB session token."""
    _invalidate_current_session_token()
    clear_session_token_cookie()


def _invalidate_current_session_token() -> None:
    """Delete the current session token from the DB (if present in cookie)."""
    token = _read_session_token_from_cookies()
    if token is None:
        return
    conn = get_db_connection()
    delete_session_token(conn, token)


def _read_session_token_from_cookies() -> str | None:
    """Read session token from CookieManager or context cookies."""
    token_ctx = peek_session_token_from_context_cookies()
    if token_ctx:
        return token_ctx
    cm = profile_cookie_manager()
    raw = cm.get(SESSION_TOKEN_COOKIE_NAME)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_session_token_from_context_cookies() -> str | None:
    """Return session token from HTTP request cookies (faster than CookieManager)."""
    try:
        raw = st.context.cookies.to_dict().get(SESSION_TOKEN_COOKIE_NAME)
    except Exception:
        return None
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def persist_spotify_oauth_state_cookie(state: str) -> None:
    """Store Spotify OAuth ``state`` for callback validation after a full page load."""
    if not isinstance(state, str) or not state.strip():
        return
    cm = profile_cookie_manager()
    cm.set(
        SPOTIFY_OAUTH_STATE_COOKIE_NAME,
        state,
        key="mr_cookie_spotify_oauth_set",
        max_age=600.0,
        same_site="lax",
    )


def peek_spotify_oauth_state_cookie() -> str | None:
    """Return the Spotify OAuth ``state`` from the browser cookie if present."""
    cm = profile_cookie_manager()
    raw = cm.get(SPOTIFY_OAUTH_STATE_COOKIE_NAME)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_spotify_oauth_state_from_context_cookies() -> str | None:
    """Return OAuth CSRF state from ``st.context.cookies`` (HTTP request).

    After an external OAuth redirect, ``extra_streamlit_components`` may not have
    mirrored document cookies into Python yet, while the Streamlit session
    request already includes cookies sent by the browser.
    """
    try:
        raw = st.context.cookies.to_dict().get(SPOTIFY_OAUTH_STATE_COOKIE_NAME)
    except Exception:
        return None
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def clear_spotify_oauth_state_cookie() -> None:
    """Remove the Spotify OAuth state cookie after success or disconnect."""
    cm = profile_cookie_manager()
    _safe_cookie_manager_delete(
        cm,
        SPOTIFY_OAUTH_STATE_COOKIE_NAME,
        key="mr_cookie_spotify_oauth_del",
    )


def persist_spotify_pkce_verifier_cookie(verifier: str) -> None:
    """Store PKCE ``code_verifier`` for the token exchange after Spotify redirect."""
    if not isinstance(verifier, str) or not verifier.strip():
        return
    cm = profile_cookie_manager()
    cm.set(
        SPOTIFY_PKCE_VERIFIER_COOKIE_NAME,
        verifier,
        key="mr_cookie_spotify_pkce_set",
        max_age=600.0,
        same_site="lax",
    )


def peek_spotify_pkce_verifier_cookie() -> str | None:
    """Return the PKCE verifier from the browser cookie if present."""
    cm = profile_cookie_manager()
    raw = cm.get(SPOTIFY_PKCE_VERIFIER_COOKIE_NAME)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_spotify_pkce_verifier_from_context_cookies() -> str | None:
    """Return PKCE verifier from ``st.context.cookies`` (OAuth return request)."""
    try:
        raw = st.context.cookies.to_dict().get(SPOTIFY_PKCE_VERIFIER_COOKIE_NAME)
    except Exception:
        return None
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def clear_spotify_pkce_verifier_cookie() -> None:
    """Remove the PKCE verifier cookie after token exchange or cancel."""
    cm = profile_cookie_manager()
    _safe_cookie_manager_delete(
        cm,
        SPOTIFY_PKCE_VERIFIER_COOKIE_NAME,
        key="mr_cookie_spotify_pkce_del",
    )


def persist_spotify_session_snapshot_cookie(payload_json: str) -> None:
    """Store taste/filter session fields for restore after OAuth (short-lived)."""
    if not isinstance(payload_json, str) or not payload_json.strip():
        return
    cm = profile_cookie_manager()
    cm.set(
        SPOTIFY_SESSION_SNAPSHOT_COOKIE_NAME,
        payload_json,
        key="mr_cookie_spotify_snapshot_set",
        max_age=600.0,
        same_site="lax",
    )


def peek_spotify_session_snapshot_from_context_cookies() -> str | None:
    """Return snapshot JSON from HTTP cookies when CookieManager lags (OAuth return)."""
    try:
        raw = st.context.cookies.to_dict().get(SPOTIFY_SESSION_SNAPSHOT_COOKIE_NAME)
    except Exception:
        return None
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def peek_spotify_session_snapshot_cookie() -> str | None:
    """Return session snapshot JSON from browser cookie if present."""
    raw_ctx = peek_spotify_session_snapshot_from_context_cookies()
    if raw_ctx:
        return raw_ctx
    cm = profile_cookie_manager()
    raw = cm.get(SPOTIFY_SESSION_SNAPSHOT_COOKIE_NAME)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def clear_spotify_session_snapshot_cookie() -> None:
    """Remove the session snapshot cookie after successful token exchange or abandon."""
    cm = profile_cookie_manager()
    _safe_cookie_manager_delete(
        cm,
        SPOTIFY_SESSION_SNAPSHOT_COOKIE_NAME,
        key="mr_cookie_spotify_snapshot_del",
    )


def apply_spotify_oauth_session_snapshot(
    session: MutableMapping[str, Any],
    data: Mapping[str, Any],
) -> None:
    """Merge Spotify OAuth snapshot dict into session (filters, communities, widgets).

    Used after an external redirect: ``bootstrap_profile_session`` may re-apply the
    saved profile from disk and wipe unsaved tweaks; the snapshot restores the
    in-tab state the user had when starting OAuth.
    """
    if data.get("snapshot_version") != 1:
        return
    fs = data.get("filter_settings")
    if isinstance(fs, dict):
        session["filter_settings"] = dict(fs)
    cw = data.get("community_weights_raw")
    if isinstance(cw, dict):
        parsed: dict[str, float] = {}
        for k, v in cw.items():
            if isinstance(v, (int, float)):
                parsed[str(k)] = float(v)
        session["community_weights_raw"] = parsed
    for key in (
        "selected_communities",
        "artist_flow_selected_communities",
        "genre_flow_selected_communities",
    ):
        raw_list = data.get(key)
        if isinstance(raw_list, list):
            session[key] = {str(x) for x in raw_list}
    fm = data.get("flow_mode")
    if fm is None or isinstance(fm, str):
        session["flow_mode"] = fm
    ft = data.get("free_text_query")
    if isinstance(ft, str):
        session["free_text_query"] = ft
    widgets = data.get("widgets")
    if isinstance(widgets, dict):
        for wkey, val in widgets.items():
            if isinstance(wkey, str) and isinstance(val, (bool, int, float, str)):
                session[wkey] = val
    if data_implies_taste_setup_complete(session):
        clear_taste_wizard_reset_pending(session)
    else:
        mark_taste_wizard_reset_pending(session)


def peek_active_profile_slug_from_context_cookies() -> str | None:
    """Resolve a profile slug from the session-token cookie (context cookies).

    Validates the token against the DB and returns the associated slug, or
    ``None`` if no valid token is present.
    """
    token = peek_session_token_from_context_cookies()
    if not token:
        return None
    conn = get_db_connection()
    return validate_session_token(conn, token)


def restore_active_profile_from_cookie_if_needed() -> None:
    """If server session lost the slug, restore login from session-token cookie."""
    if st.session_state.get(ACTIVE_PROFILE_SESSION_KEY):
        return
    token = _read_session_token_from_cookies()
    if not token:
        return
    conn = get_db_connection()
    slug = validate_session_token(conn, token)
    if slug is None:
        clear_session_token_cookie()
        return
    data = load_user_profile(conn, slug)
    st.session_state[ACTIVE_PROFILE_SESSION_KEY] = slug
    if data is not None:
        apply_profile_to_session(st.session_state, data)


def bootstrap_profile_session() -> None:
    """Restore profile from session-token cookie and re-hydrate (entrypoint only)."""
    restore_active_profile_from_cookie_if_needed()
    res = ensure_active_profile_hydrated(st.session_state)
    if res == ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE:
        clear_session_token_cookie()
        st.warning(
            "Gespeichertes Profil wurde nicht gefunden. "
            "Die Anmeldung wurde zurückgesetzt (Cookie entfernt).",
        )


def render_profile_sidebar() -> None:
    """Profile status and actions in the sidebar (entrypoint; runs every rerun)."""
    res = ensure_active_profile_hydrated(st.session_state)
    if res == ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE:
        clear_session_token_cookie()

    st.sidebar.markdown("### Profil")
    active = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if active:
        st.sidebar.caption(f"Angemeldet als **{active}**")
        if st.sidebar.button(
            "Speichern",
            key="sb_prof_save",
            use_container_width=True,
        ):
            save_current_profile_to_disk()
        if st.sidebar.button(
            "Filter und Stile zurücksetzen",
            key="sb_prof_reset",
            use_container_width=True,
        ):
            reset_taste_preferences()
            st.rerun()
        if st.sidebar.button(
            "Abmelden",
            key="sb_prof_logout",
            use_container_width=True,
        ):
            logout_active_profile()
            st.rerun()
    else:
        st.sidebar.caption("Kein Profil aktiv")
        # Use switch_page, not page_link: after OAuth return URLs with query
        # params, Streamlit's page_link registry can lack url_pathname and raise.
        if st.sidebar.button(
            "Anmelden",
            key="sb_prof_login",
            use_container_width=True,
        ):
            st.switch_page("pages/0_Profil.py")


def render_toolbar(page_key: str) -> None:
    """Reserved hook at page top; profile controls live in the entrypoint sidebar."""
    _ = page_key
