"""Build Spotify playlist candidates from newest reviews.

Logging uses ``music_review.dashboard.newest_spotify_playlist`` (English messages).
INFO: pool weights summary and build start/finish plus skip counters. WARNING:
skipped slots (no track, Spotify unresolved, duplicate URI) and strict-resolve
failures. DEBUG: each album draw, picked title, successful slot, search query,
and per-album weight lines. Enable DEBUG on that logger to trace the full
selection loop in the Streamlit process (e.g. configure root logging or set the
logger level before ``streamlit run``).
"""

from __future__ import annotations

import logging
import math
import random
import re
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol

from music_review.domain.models import Review, Track
from music_review.integrations.spotify_client import (
    SpotifyClient,
    SpotifyToken,
    SpotifyTrack,
)

LOGGER = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")

_LOG_STR_MAX = 120

# Trailing credit suffixes plattentests.de often appends; Spotify wording may differ.
_TRAILING_FEAT_PAREN_RE = re.compile(
    r"""(?ix)
    \s*
    [\(\[]
    \s*
    (?:feat\.?|featuring|ft\.?)\s+
    [^\)\]]+
    [\)\]]
    \s*$
    """,
)
_TRAILING_FEAT_UNPAREN_RE = re.compile(
    r"""(?ix)
    \s+
    \b(?:feat\.?|featuring|ft\.?)\b
    \s+
    .+$
    """,
)
_FEAT_KEYWORD_RE = re.compile(r"(?i)\b(?:feat\.?|featuring|ft\.)\b")
# Plattentests: ``(Lanark Artefak remix)``; Spotify often ``- Lanark Artefak Remix``.
_REMIX_TRAILING_PAREN_RE = re.compile(
    r"(?is)\s*[\(\[]\s*[^]\)]*?\bremix\s*[\]\)]\s*$",
)
_REMIX_TRAILING_DASH_RE = re.compile(r"(?is)\s*-\s*.+\bremix\s*$")

# Suffix match: avoid accepting very short Spotify titles.
_MIN_SUFFIX_TITLE_CHARS = 5


def _log_str(value: str, *, max_len: int = _LOG_STR_MAX) -> str:
    """Truncate long strings for log lines."""
    s = value.replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return f"{s[: max_len - 3]}..."


def _fold_umlauts_ascii(s: str) -> str:
    """Map common German letters to ASCII for matching and fallback search."""
    out = s
    for old, new in (
        ("ä", "a"),
        ("ö", "o"),
        ("ü", "u"),
        ("Ä", "A"),
        ("Ö", "O"),
        ("Ü", "U"),
        ("ß", "ss"),
    ):
        out = out.replace(old, new)
    return out


def _norm_for_match(value: str) -> str:
    """Normalize for title/artist equality (case, punctuation, umlaut folding)."""
    return _norm_text(_fold_umlauts_ascii(value))


def _strip_trailing_feat_credit_suffixes(title: str) -> str:
    """Remove trailing (feat. ...) / [ft. ...] or trailing ``feat. Name`` segments."""
    t = title.strip()
    while True:
        new_t = _TRAILING_FEAT_PAREN_RE.sub("", t)
        new_t = _TRAILING_FEAT_UNPAREN_RE.sub("", new_t).rstrip()
        if new_t == t:
            break
        t = new_t
    return t.strip()


def _title_has_feat_keyword(title: str) -> bool:
    return bool(_FEAT_KEYWORD_RE.search(title))


def _strip_trailing_remix_clauses(title: str) -> str:
    """Remove trailing remix credits (parenthetical or `` - … Remix``)."""
    t = title.strip()
    while True:
        new_t = _REMIX_TRAILING_PAREN_RE.sub("", t).strip()
        new_t = _REMIX_TRAILING_DASH_RE.sub("", new_t).strip()
        if new_t == t:
            break
        t = new_t
    return t


def _review_title_suffix_matches_spotify(
    review_title: str,
    spotify_track_name: str,
) -> bool:
    """Spotify title matches the trailing tokens of the review title."""
    r_tokens = _norm_for_match(review_title).split()
    s_tokens = _norm_for_match(spotify_track_name).split()
    if not s_tokens or len(s_tokens) > len(r_tokens):
        return False
    if r_tokens[-len(s_tokens) :] != s_tokens:
        return False
    return len(" ".join(s_tokens)) >= _MIN_SUFFIX_TITLE_CHARS


def _titles_match_review_vs_spotify(review_title: str, spotify_track_name: str) -> bool:
    if _norm_for_match(review_title) == _norm_for_match(spotify_track_name):
        return True

    review_feat = _title_has_feat_keyword(review_title)
    spotify_feat = _title_has_feat_keyword(spotify_track_name)
    if review_feat or spotify_feat:
        base_r = _strip_trailing_feat_credit_suffixes(review_title)
        base_s = _strip_trailing_feat_credit_suffixes(spotify_track_name)
        if base_r and base_s and _norm_for_match(base_r) == _norm_for_match(base_s):
            return True

    cr = _strip_trailing_remix_clauses(review_title)
    cs = _strip_trailing_remix_clauses(spotify_track_name)
    if cr and cs and _norm_for_match(cr) == _norm_for_match(cs):
        return True

    return _review_title_suffix_matches_spotify(review_title, spotify_track_name)


def _artist_query_candidates(artist: str) -> list[str]:
    """Full name plus each ``/`` segment for Spotify queries."""
    a = artist.strip()
    if not a:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for cand in (a, *re.split(r"\s*/\s*", a)):
        c = cand.strip()
        if not c:
            continue
        key = c.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _track_title_query_candidates(track_title: str) -> list[str]:
    """Full title plus feat- and remix-stripped forms (deduped, stable order)."""
    t = track_title.strip()
    if not t:
        return []
    tf = _strip_trailing_feat_credit_suffixes(t)
    tr = _strip_trailing_remix_clauses(t)
    t_both = _strip_trailing_feat_credit_suffixes(tr)
    pool = (t, tf, tr, t_both)
    out: list[str] = []
    seen: set[str] = set()
    for c in pool:
        c = c.strip()
        if not c:
            continue
        key = c.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _artist_matches_review_vs_spotify(
    review_artist: str,
    spotify_artists: tuple[str, ...],
) -> bool:
    needle = _norm_for_match(review_artist)
    if not needle:
        return False
    norms = [_norm_for_match(a) for a in spotify_artists]
    blob = " ".join(norms)
    if any(needle in n for n in norms) or needle in blob:
        return True
    for seg in re.split(r"\s*/\s*", review_artist.strip()):
        s = _norm_for_match(seg)
        if len(s) >= 3 and (any(s in n for n in norms) or s in blob):
            return True
    return False


def spotify_resolve_query_variants(artist: str, track_title: str) -> list[str]:
    """Build Spotify search strings: quoted fields, ASCII fold, then loose text.

    Tries **each** slash-separated artist segment and several track shapes (full,
    feat-stripped, remix-stripped) so Spotify naming and plattentests tracklists
    align more often.
    """
    variants: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            variants.append(q)

    def add_shapes_for(a_raw: str, t_raw: str) -> None:
        a_loc = a_raw.strip()
        t_loc = t_raw.strip()
        a_fold = _fold_umlauts_ascii(a_loc)
        t_fold = _fold_umlauts_ascii(t_loc)
        add(f'artist:"{a_loc}" track:"{t_loc}"')
        if a_fold != a_loc or t_fold != t_loc:
            add(f'artist:"{a_fold}" track:"{t_fold}"')
        add(f"{a_loc} {t_loc}")
        if a_fold != a_loc or t_fold != t_loc:
            add(f"{a_fold} {t_fold}")

    for a_try in _artist_query_candidates(artist):
        for t_try in _track_title_query_candidates(track_title):
            add_shapes_for(a_try, t_try)
    return variants


def _pick_track_uri_from_search_results(
    results: list[SpotifyTrack],
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Pick one URI: all title/artist matches use the first; else sole API row."""
    plausible = [
        r
        for r in results
        if _titles_match_review_vs_spotify(track_title, r.name)
        and _artist_matches_review_vs_spotify(artist, r.artists)
    ]
    if len(plausible) >= 1:
        chosen = plausible[0]
        if len(plausible) > 1:
            LOGGER.info(
                "Spotify resolve: multiple matching tracks, using first "
                "n=%s first_id=%s",
                len(plausible),
                chosen.id,
            )
        LOGGER.debug(
            "Spotify resolve: accepted match track_id=%s title=%r",
            chosen.id,
            _log_str(chosen.name, max_len=80),
        )
        return chosen.uri
    if len(results) == 1:
        only = results[0]
        LOGGER.debug(
            "Spotify resolve: accepted sole API result track_id=%s title=%r",
            only.id,
            _log_str(only.name, max_len=80),
        )
        return only.uri
    LOGGER.debug(
        "Spotify resolve: no usable match in this result set "
        "n_results=%s n_plausible=%s artist=%r track=%r top_titles=%s",
        len(results),
        len(plausible),
        _log_str(artist),
        _log_str(track_title),
        [_log_str(r.name, max_len=40) for r in results[:5]],
    )
    return None


class ResolveTrackUriFn(Protocol):
    """Callable signature for strict track resolution."""

    def __call__(self, *, artist: str, track_title: str) -> str | None: ...


@dataclass(slots=True)
class PlaylistCandidate:
    """One generated playlist item before saving to Spotify."""

    review_id: int
    artist: str
    album: str
    track_title: str
    source_kind: str
    spotify_uri: str
    score_weight: float
    raw_score: float
    playlist_slot_quota: int
    strat_ideal_slots: float
    strat_floor_slots: int
    strat_remainder_extra_slots: int


@dataclass(slots=True)
class StratifiedSlotPlan:
    """Per-album breakdown from normalized weights to integer slot quota."""

    ideal_slots: float
    floor_slots: int
    remainder_extra_slots: int
    quota: int


def _norm_text(value: str) -> str:
    clean = _NON_WORD_RE.sub(" ", value.casefold())
    return _SPACE_RE.sub(" ", clean).strip()


def catalog_lookup_key(artist: str, track_title: str) -> str:
    """Stable key for cross-provider catalog caches.

    Matches duplicate-track detection inside :func:`build_playlist_candidates`
    (``artist`` + ``track_title`` from the review source).
    """
    return f"{_norm_text(artist)}::{_norm_text(track_title)}"


def build_album_weights(
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
) -> tuple[list[Review], list[float], list[float]]:
    """Return reviews, normalized weights (sum 1), and raw non-negative scores.

    When ``ranked_rows`` is set, the returned list follows **row order** (same as
    the ranked UI), not the order of the ``reviews`` argument. Each weight is
    ``max(0, overall_score) / sum(...)``, so scores ``0.3, 0.1, 0.1`` become
    ``3/5, 1/5, 1/5``. Raw values are those ``max(0, overall_score)`` inputs
    before normalization. :func:`build_playlist_candidates` turns weights into
    **integer slot counts** per album (largest remainder).

    Uniform fallbacks use raw ``1.0`` per album so relative weights are equal
    before normalization.
    """
    if not reviews:
        LOGGER.info("Album weights: empty review list")
        return [], [], []
    if not ranked_rows:
        w = 1.0 / float(len(reviews))
        raw = [1.0 for _ in reviews]
        LOGGER.info(
            "Album weights: uniform (no ranking) pool_size=%s weight_each=%.6f",
            len(reviews),
            w,
        )
        LOGGER.debug(
            "Album weights: uniform mode review_ids_sample=%s",
            [int(r.id) for r in reviews[:8]],
        )
        return reviews, [w for _ in reviews], raw

    picked_reviews: list[Review] = []
    raw_weights: list[float] = []
    for row in ranked_rows:
        review = row.get("review")
        if not isinstance(review, Review):
            continue
        score_any = row.get("overall_score")
        if isinstance(score_any, (int, float)):
            score = max(0.0, float(score_any))
        else:
            score = 0.0
        picked_reviews.append(review)
        raw_weights.append(score)

    if not picked_reviews:
        w = 1.0 / float(len(reviews))
        raw_uniform = [1.0 for _ in reviews]
        LOGGER.warning(
            "Album weights: ranked rows had no valid reviews; uniform fallback "
            "pool_size=%s",
            len(reviews),
        )
        return reviews, [w for _ in reviews], raw_uniform

    total = sum(raw_weights)
    if total <= 0.0:
        w = 1.0 / float(len(picked_reviews))
        raw_uniform = [1.0 for _ in picked_reviews]
        LOGGER.warning(
            "Album weights: all scores zero or negative; uniform over %s ranked rows",
            len(picked_reviews),
        )
        return picked_reviews, [w for _ in picked_reviews], raw_uniform
    norm_weights = [w / total for w in raw_weights]
    LOGGER.info(
        "Album weights: from overall_score pool_size=%s raw_total=%.6f",
        len(picked_reviews),
        total,
    )
    LOGGER.debug(
        "Album weights: preference mode norm_weight min=%.6f max=%.6f "
        "raw_score min=%.6f max=%.6f",
        min(norm_weights),
        max(norm_weights),
        min(raw_weights),
        max(raw_weights),
    )
    for rev, nw, rw in zip(picked_reviews, norm_weights, raw_weights, strict=True):
        LOGGER.debug(
            "Album weight detail review_id=%s weight=%.6f raw_score=%.6f "
            "artist=%r album=%r",
            rev.id,
            nw,
            rw,
            _log_str(rev.artist, max_len=60),
            _log_str(rev.album, max_len=60),
        )
    return picked_reviews, norm_weights, raw_weights


def amplify_preference_weights(
    weights: list[float],
    *,
    exponent: float = 2.0,
) -> list[float]:
    """Apply a convex reweighting so larger weights gain extra slot share.

    Each non-negative weight is raised to ``exponent`` and the vector is
    renormalized to sum 1. For ``exponent`` > 1, high-scoring albums receive
    disproportionately more stratified slots than under linear weights. For
    ``exponent`` <= 1 or an empty list, returns a shallow copy of ``weights``.

    If the sum of powered weights is zero, returns a copy of ``weights``.
    """
    if not weights or exponent <= 1.0:
        return list(weights)
    powered = [max(0.0, float(w)) ** float(exponent) for w in weights]
    total_p = float(sum(powered))
    if total_p <= 0.0:
        return list(weights)
    return [p / total_p for p in powered]


def build_stratified_slot_plans(
    weights: list[float],
    target_count: int,
) -> list[StratifiedSlotPlan]:
    """Compute ideal fractional slots, floors, remainder extras, and final quotas.

    Uses the largest-remainder method when weight sums are positive: each album
    gets ``floor(ideal)`` plus at most one extra slot for the largest fractional
    remainders (ties: higher album index first). When all weights are zero,
    falls back to an even split (first ``target_count % n`` albums get +1).
    """
    n = len(weights)
    if n == 0:
        return []
    if target_count <= 0:
        return [StratifiedSlotPlan(0.0, 0, 0, 0) for _ in range(n)]

    total_w = float(sum(weights))
    if total_w <= 0.0:
        base = target_count // n
        extra = target_count % n
        ideal_each = float(target_count) / float(n)
        return [
            StratifiedSlotPlan(
                ideal_slots=ideal_each,
                floor_slots=base,
                remainder_extra_slots=1 if i < extra else 0,
                quota=base + (1 if i < extra else 0),
            )
            for i in range(n)
        ]

    raw = [target_count * (float(w) / total_w) for w in weights]
    floors = [math.floor(r) for r in raw]
    remainder = target_count - sum(floors)
    frac_order = sorted(
        range(n),
        key=lambda i: (raw[i] - floors[i], i),
        reverse=True,
    )
    extra_by_idx = [0 for _ in range(n)]
    for j in range(remainder):
        extra_by_idx[frac_order[j]] += 1
    return [
        StratifiedSlotPlan(
            ideal_slots=raw[i],
            floor_slots=floors[i],
            remainder_extra_slots=extra_by_idx[i],
            quota=floors[i] + extra_by_idx[i],
        )
        for i in range(n)
    ]


def allocate_stratified_slot_counts(
    weights: list[float],
    target_count: int,
) -> list[int]:
    """Split ``target_count`` slots across albums proportionally to ``weights``.

    Same rules as :func:`build_stratified_slot_plans`; returns only the quotas.
    """
    return [p.quota for p in build_stratified_slot_plans(weights, target_count)]


def review_has_unused_track_candidate(
    review: Review,
    already_picked_keys: set[str],
) -> bool:
    """True if the review has a track whose key is not in ``already_picked_keys``."""
    highlights, non_highlights = candidate_tracks_for_review(review)
    for track in (*highlights, *non_highlights):
        key = catalog_lookup_key(review.artist, track.title)
        if key not in already_picked_keys:
            return True
    return False


def next_album_index_with_unused_tracks_cyclic(
    reviews: list[Review],
    *,
    after_index: int,
    skip_indices: set[int],
    picked_song_keys: set[str],
) -> int | None:
    """Next pool index after ``after_index`` (cyclic) with an unused track.

    Skips indices in ``skip_indices``. Returns ``None`` if no other album can
    contribute a track (including single-album pools).
    """
    n = len(reviews)
    if n <= 1:
        return None
    for step in range(1, n):
        idx = (after_index + step) % n
        if idx in skip_indices:
            continue
        if review_has_unused_track_candidate(reviews[idx], picked_song_keys):
            return idx
    return None


def candidate_tracks_for_review(review: Review) -> tuple[list[Track], list[Track]]:
    """Split a review's tracklist into highlights and non-highlights."""
    if not review.tracklist:
        return [], []
    highlights: list[Track] = [t for t in review.tracklist if t.is_highlight]
    if not highlights and review.highlights:
        hs = {_norm_text(name) for name in review.highlights if name.strip()}
        highlights = [t for t in review.tracklist if _norm_text(t.title) in hs]
    non_highlights = [t for t in review.tracklist if t not in highlights]
    return highlights, non_highlights


def pick_track_title_for_iteration(
    review: Review,
    *,
    already_picked_keys: set[str],
    rng: random.Random,
) -> tuple[str, str] | None:
    """Pick one track title for a review.

    Returns ``(track_title, source_kind)`` where source kind is ``highlight`` or
    ``fallback``.
    """
    highlights, non_highlights = candidate_tracks_for_review(review)

    def _pick_from(candidates: list[Track], source_kind: str) -> tuple[str, str] | None:
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        for track in shuffled:
            key = catalog_lookup_key(review.artist, track.title)
            if key in already_picked_keys:
                continue
            return track.title, source_kind
        return None

    highlight_pick = _pick_from(highlights, "highlight")
    if highlight_pick is not None:
        return highlight_pick
    return _pick_from(non_highlights, "fallback")


def resolve_track_uri_strict(
    client: SpotifyClient,
    token: SpotifyToken,
    *,
    artist: str,
    track_title: str,
) -> str | None:
    """Resolve a track URI via Spotify search.

    Tries several query shapes (quoted fields, ASCII-folded umlauts, loose text,
    slash-separated artists, feat- and remix-stripped titles) so credits and
    spelling differ from Spotify.
    When several API rows match the same normalized title and artist, the
    **first** hit is kept (duplicate releases / regional duplicates).
    """
    queries = spotify_resolve_query_variants(artist, track_title)
    for variant_index, query in enumerate(queries):
        LOGGER.debug(
            "Spotify resolve: query variant=%s q=%r",
            variant_index,
            _log_str(query, max_len=220),
        )
        results = client.search_tracks(query=query, limit=5, token=token)
        if not results:
            continue
        picked = _pick_track_uri_from_search_results(
            results,
            artist=artist,
            track_title=track_title,
        )
        if picked:
            if variant_index > 0:
                LOGGER.info(
                    "Spotify resolve: match via fallback query variant_index=%s",
                    variant_index,
                )
            return picked
    LOGGER.warning(
        "Spotify resolve: no results after %s query variants artist=%r track=%r",
        len(queries),
        _log_str(artist),
        _log_str(track_title),
    )
    return None


def build_playlist_candidates(
    *,
    reviews: list[Review],
    weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    resolve_fn: ResolveTrackUriFn,
    resolve_retries_per_album: int = 2,
    max_attempt_factor: int = 20,
) -> list[PlaylistCandidate]:
    """Generate playlist candidates with stratified album quotas.

    Normalized ``weights`` and parallel ``raw_scores`` (same length as ``reviews``)
    define each album's **share** of ``target_count`` slots via
    :func:`allocate_stratified_slot_counts`. ``raw_scores`` are stored on each
    candidate for display (e.g. UI table); only ``weights`` affect allocation.
    Slot order is shuffled so the final list is not grouped by album.

    Slots are stored in a queue (shuffled album indices). For each slot, picks
    are random among unused highlights, then non-highlights. After
    ``resolve_retries_per_album`` failed Spotify resolutions (or duplicate URIs)
    on the **same** album, the front slot is reassigned to the next pool album
    (cyclic) that still has an unused track. If no album can fill the slot, it
    is dropped. ``max_attempt_factor`` caps total loop iterations as
    ``target_count * max_attempt_factor`` as a safety net.
    """
    if not reviews or not weights or not raw_scores or target_count <= 0:
        LOGGER.info(
            "Playlist candidate build skipped: empty inputs "
            "reviews=%s weights=%s raw_scores=%s target_count=%s",
            len(reviews),
            len(weights),
            len(raw_scores),
            target_count,
        )
        return []

    if len(reviews) != len(weights) or len(reviews) != len(raw_scores):
        LOGGER.warning(
            "Playlist candidate build skipped: parallel list length mismatch "
            "reviews=%s weights=%s raw_scores=%s",
            len(reviews),
            len(weights),
            len(raw_scores),
        )
        return []

    results: list[PlaylistCandidate] = []
    picked_song_keys: set[str] = set()
    picked_uris: set[str] = set()
    score_weight_by_id = {
        int(r.id): float(w) for r, w in zip(reviews, weights, strict=True)
    }

    skip_no_track = 0
    skip_unresolved = 0
    skip_dup_uri = 0
    skip_abandoned_slots = 0
    slot_album_fallbacks = 0

    strat_plans = build_stratified_slot_plans(weights, target_count)
    quotas = [p.quota for p in strat_plans]
    slot_album_indices: list[int] = []
    for album_idx, q in enumerate(quotas):
        slot_album_indices.extend([album_idx] * q)
    assert len(slot_album_indices) == target_count
    rng.shuffle(slot_album_indices)

    pending_slots: deque[int] = deque(slot_album_indices)
    slot_resolve_failures = 0
    dead_albums_for_slot: set[int] = set()
    per_album_resolve_cap = max(1, int(resolve_retries_per_album))

    max_attempts = max(target_count * max_attempt_factor, target_count)
    attempts = 0
    LOGGER.info(
        "Playlist candidate build start target_count=%s pool_albums=%s "
        "stratified_quotas=%s max_attempts=%s resolve_retries_per_album=%s",
        target_count,
        len(reviews),
        quotas,
        max_attempts,
        per_album_resolve_cap,
    )

    def _abandon_current_slot(*, reason: str, **details: object) -> None:
        nonlocal skip_abandoned_slots, slot_resolve_failures
        pending_slots.popleft()
        skip_abandoned_slots += 1
        slot_resolve_failures = 0
        dead_albums_for_slot.clear()
        LOGGER.warning(
            "Playlist abandon slot: %s filled=%s pending=%s review_id=%s "
            "artist=%r album=%r %s",
            reason,
            len(results),
            len(pending_slots),
            review.id,
            _log_str(review.artist, max_len=80),
            _log_str(review.album, max_len=80),
            " ".join(f"{k}={v!r}" for k, v in details.items()),
        )

    def _try_assign_next_album_for_slot() -> bool:
        """Move front slot to the next cyclic album with an unused track.

        Adds ``album_idx`` to ``dead_albums_for_slot`` first. Returns True if
        reassigned, False if no fallback album exists.
        """
        nonlocal slot_album_fallbacks, slot_resolve_failures
        dead_albums_for_slot.add(album_idx)
        nxt = next_album_index_with_unused_tracks_cyclic(
            reviews,
            after_index=album_idx,
            skip_indices=dead_albums_for_slot,
            picked_song_keys=picked_song_keys,
        )
        if nxt is None:
            return False
        pending_slots[0] = nxt
        slot_resolve_failures = 0
        slot_album_fallbacks += 1
        LOGGER.info(
            "Playlist slot: album fallback from_idx=%s to_idx=%s review_ids %s->%s",
            album_idx,
            nxt,
            reviews[album_idx].id,
            reviews[nxt].id,
        )
        return True

    while pending_slots and attempts < max_attempts:
        attempts += 1
        album_idx = pending_slots[0]
        review = reviews[album_idx]
        w_album = score_weight_by_id.get(int(review.id), 0.0)
        LOGGER.debug(
            "Playlist draw attempt=%s filled=%s/%s pending=%s album_idx=%s "
            "review_id=%s album_weight=%.6f artist=%r album=%r",
            attempts,
            len(results),
            target_count,
            len(pending_slots),
            album_idx,
            review.id,
            w_album,
            _log_str(review.artist, max_len=80),
            _log_str(review.album, max_len=80),
        )
        picked = pick_track_title_for_iteration(
            review,
            already_picked_keys=picked_song_keys,
            rng=rng,
        )
        if picked is None:
            skip_no_track += 1
            hl, nh = candidate_tracks_for_review(review)
            if _try_assign_next_album_for_slot():
                continue
            _abandon_current_slot(
                reason="no_unused_track_pool_exhausted",
                highlights=len(hl),
                non_highlights=len(nh),
                tracklist_len=len(review.tracklist),
            )
            continue
        track_title, source_kind = picked
        LOGGER.debug(
            "Playlist pick track review_id=%s title=%r source_kind=%s",
            review.id,
            _log_str(track_title, max_len=100),
            source_kind,
        )
        uri = resolve_fn(artist=review.artist, track_title=track_title)
        if not isinstance(uri, str) or not uri:
            skip_unresolved += 1
            LOGGER.debug(
                "Playlist skip: resolver returned empty review_id=%s track=%r",
                review.id,
                _log_str(track_title, max_len=100),
            )
            slot_resolve_failures += 1
            if slot_resolve_failures >= per_album_resolve_cap:
                if _try_assign_next_album_for_slot():
                    continue
                _abandon_current_slot(
                    reason="resolve_failures_no_fallback_album",
                    tries=per_album_resolve_cap,
                    last_track=_log_str(track_title, max_len=100),
                )
            continue
        if uri in picked_uris:
            skip_dup_uri += 1
            LOGGER.debug(
                "Playlist skip: duplicate spotify uri review_id=%s uri=%r track=%r",
                review.id,
                _log_str(uri, max_len=80),
                _log_str(track_title, max_len=80),
            )
            slot_resolve_failures += 1
            if slot_resolve_failures >= per_album_resolve_cap:
                if _try_assign_next_album_for_slot():
                    continue
                _abandon_current_slot(
                    reason="duplicate_uri_no_fallback_album",
                    tries=per_album_resolve_cap,
                    last_track=_log_str(track_title, max_len=80),
                )
            continue
        key = catalog_lookup_key(review.artist, track_title)
        picked_song_keys.add(key)
        picked_uris.add(uri)
        pending_slots.popleft()
        slot_resolve_failures = 0
        dead_albums_for_slot.clear()
        plan = strat_plans[album_idx]
        results.append(
            PlaylistCandidate(
                review_id=int(review.id),
                artist=review.artist,
                album=review.album,
                track_title=track_title,
                source_kind=source_kind,
                spotify_uri=uri,
                score_weight=score_weight_by_id.get(int(review.id), 0.0),
                raw_score=float(raw_scores[album_idx]),
                playlist_slot_quota=int(plan.quota),
                strat_ideal_slots=float(plan.ideal_slots),
                strat_floor_slots=int(plan.floor_slots),
                strat_remainder_extra_slots=int(plan.remainder_extra_slots),
            ),
        )
        LOGGER.debug(
            "Playlist slot filled %s/%s review_id=%s source=%s track=%r",
            len(results),
            target_count,
            review.id,
            source_kind,
            _log_str(track_title, max_len=80),
        )

    if pending_slots:
        LOGGER.warning(
            "Playlist candidate build hit global attempt limit: "
            "unfilled_slots=%s filled=%s target=%s attempts_used=%s "
            "album_fallbacks=%s abandoned_slots=%s skip_no_track=%s "
            "skip_unresolved=%s skip_dup_uri=%s",
            len(pending_slots),
            len(results),
            target_count,
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_unresolved,
            skip_dup_uri,
        )
    elif len(results) < target_count:
        LOGGER.warning(
            "Playlist candidate build stopped early: filled=%s target=%s "
            "attempts_used=%s album_fallbacks=%s abandoned_slots=%s "
            "skip_no_track=%s skip_unresolved=%s skip_dup_uri=%s",
            len(results),
            target_count,
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_unresolved,
            skip_dup_uri,
        )
    else:
        LOGGER.info(
            "Playlist candidate build complete: filled=%s attempts_used=%s "
            "album_fallbacks=%s abandoned_slots=%s skip_no_track=%s "
            "skip_unresolved=%s skip_dup_uri=%s",
            len(results),
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_unresolved,
            skip_dup_uri,
        )
    return results
