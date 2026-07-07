"""Build playlist track suggestions from review corpora (no streaming APIs).

Logging uses ``music_review.dashboard.playlist_builder`` (English messages).
"""

from __future__ import annotations

import logging
import math
import random
import re
import sys
from collections import deque
from dataclasses import dataclass
from typing import Any, Literal

from music_review.domain.models import Review, Track

SelectionStrategy = Literal["stratified", "weighted_sample"]
AlbumSpreadMode = Literal["variety", "balanced", "deep"]

LOGGER = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")

_LOG_STR_MAX = 120


def _log_str(value: str, *, max_len: int = _LOG_STR_MAX) -> str:
    """Truncate long strings for log lines."""
    s = value.replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return f"{s[: max_len - 3]}..."


@dataclass(slots=True)
class PlaylistSuggestion:
    """One suggested playlist item from the review corpus."""

    review_id: int
    artist: str
    album: str
    track_title: str
    source_kind: str
    score_weight: float
    raw_score: float
    playlist_slot_quota: int
    strat_ideal_slots: float
    strat_floor_slots: int
    strat_remainder_extra_slots: int
    release_year: int | None = None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class AlbumSpreadLimits:
    """Hard per-album caps enforced while filling playlist slots."""

    max_tracks_per_album: int
    max_distinct_albums: int | None = None
    caps_by_pool_index: dict[int, int] | None = None


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
    """Stable key for duplicate-track detection within one suggestion run."""
    return f"{_norm_text(artist)}::{_norm_text(track_title)}"


def build_album_weights(
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
) -> tuple[list[Review], list[float], list[float]]:
    """Return reviews, normalized weights (sum 1), and raw non-negative scores."""
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
    return picked_reviews, norm_weights, raw_weights


def amplify_preference_weights(
    weights: list[float],
    *,
    exponent: float = 2.0,
) -> list[float]:
    """Apply convex reweighting so larger weights gain extra slot share."""
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
    """Compute ideal fractional slots, floors, remainder extras, and final quotas."""
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
    """Split ``target_count`` slots across albums proportionally to ``weights``."""
    return [p.quota for p in build_stratified_slot_plans(weights, target_count)]


def weighted_sample_album_indices_without_replacement(
    weights: list[float],
    target_count: int,
    rng: random.Random,
) -> list[int]:
    """Pick album indices via Efraimidis-Spirakis weighted sampling."""
    if target_count <= 0 or not weights:
        return []

    positive_indices = [i for i, w in enumerate(weights) if float(w) > 0.0]

    if not positive_indices:
        all_indices = list(range(len(weights)))
        rng.shuffle(all_indices)
        without = all_indices[:target_count]
        if len(without) >= target_count:
            return without
        extras = [
            rng.choice(range(len(weights))) for _ in range(target_count - len(without))
        ]
        return without + extras

    keyed: list[tuple[float, int]] = []
    for idx in positive_indices:
        u = rng.random()
        if u <= 0.0:
            u = sys.float_info.min
        keyed.append((math.log(u) / float(weights[idx]), idx))
    keyed.sort(reverse=True)
    distinct_picks = [i for _, i in keyed[: min(target_count, len(positive_indices))]]

    if len(distinct_picks) >= target_count:
        return distinct_picks

    extras_pool = positive_indices
    extras_weights = [float(weights[i]) for i in extras_pool]
    extras_needed = target_count - len(distinct_picks)
    extras = rng.choices(extras_pool, weights=extras_weights, k=extras_needed)
    return distinct_picks + extras


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


def primary_review_label(review: Review) -> str | None:
    """Return the first non-empty Plattenlabel on a review."""
    for label in review.labels:
        if isinstance(label, str) and label.strip():
            return label.strip()
    return None


def album_spread_limits(
    mode: AlbumSpreadMode,
    *,
    target_count: int,
) -> AlbumSpreadLimits:
    """Map UI archive spread presets to default builder enforcement rules."""
    _ = target_count
    if mode == "variety":
        return AlbumSpreadLimits(max_tracks_per_album=1)
    if mode == "balanced":
        return AlbumSpreadLimits(max_tracks_per_album=3)
    return AlbumSpreadLimits(max_tracks_per_album=4)


def _deep_cap_for_rank(rank: int) -> int:
    """Graduated per-album cap for the deep spread preset (by score rank)."""
    if rank <= 1:
        return 4
    if rank <= 3:
        return 3
    if rank <= 7:
        return 2
    return 1


def _balanced_cap_for_rank(rank: int) -> int:
    """Graduated per-album cap for the balanced spread preset (by score rank)."""
    if rank <= 2:
        return 3
    if rank <= 11:
        return 2
    return 1


def build_graduated_caps_by_pool_index(
    mode: AlbumSpreadMode,
    weights: list[float],
) -> dict[int, int]:
    """Assign per-pool-index track caps sorted by descending album weight."""
    if not weights:
        return {}
    if mode == "variety":
        return dict.fromkeys(range(len(weights)), 1)
    ranked = sorted(range(len(weights)), key=lambda i: weights[i], reverse=True)
    cap_for_rank = _balanced_cap_for_rank if mode == "balanced" else _deep_cap_for_rank
    return {pool_idx: cap_for_rank(rank) for rank, pool_idx in enumerate(ranked)}


def _spread_cap_for_pool_index(
    album_idx: int,
    spread_limits: AlbumSpreadLimits | None,
) -> int | None:
    """Return the active per-album track cap, if any."""
    if spread_limits is None:
        return None
    if spread_limits.caps_by_pool_index is not None:
        return spread_limits.caps_by_pool_index.get(album_idx, 1)
    return spread_limits.max_tracks_per_album


def _album_can_accept_more(
    review: Review,
    *,
    album_idx: int,
    tracks_per_review_id: dict[int, int],
    albums_used: set[int],
    spread_limits: AlbumSpreadLimits | None,
) -> bool:
    """True when spread rules still allow another track from this review."""
    if spread_limits is None:
        return True
    review_id = int(review.id)
    cap = _spread_cap_for_pool_index(album_idx, spread_limits)
    if cap is not None and tracks_per_review_id.get(review_id, 0) >= cap:
        return False
    if spread_limits.caps_by_pool_index is not None:
        return True
    return not (
        spread_limits.max_distinct_albums is not None
        and review_id not in albums_used
        and len(albums_used) >= spread_limits.max_distinct_albums
    )


def _cap_stratified_slot_plans(
    plans: list[StratifiedSlotPlan],
    max_tracks_per_album: int,
    caps_by_pool_index: dict[int, int] | None = None,
) -> list[StratifiedSlotPlan]:
    """Limit per-album slot quotas before track picking starts."""
    capped: list[StratifiedSlotPlan] = []
    for album_idx, plan in enumerate(plans):
        per_album_cap = (
            caps_by_pool_index.get(album_idx, max_tracks_per_album)
            if caps_by_pool_index is not None
            else max_tracks_per_album
        )
        quota = min(plan.quota, per_album_cap)
        floor_slots = min(plan.floor_slots, quota)
        remainder_extra_slots = max(0, quota - floor_slots)
        capped.append(
            StratifiedSlotPlan(
                ideal_slots=plan.ideal_slots,
                floor_slots=floor_slots,
                remainder_extra_slots=remainder_extra_slots,
                quota=quota,
            ),
        )
    return capped


def next_album_index_with_unused_tracks_cyclic(
    reviews: list[Review],
    *,
    after_index: int,
    skip_indices: set[int],
    picked_song_keys: set[str],
) -> int | None:
    """Next pool index after ``after_index`` (cyclic) with an unused track."""
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


def next_album_index_with_capacity_cyclic(
    reviews: list[Review],
    *,
    after_index: int,
    skip_indices: set[int],
    picked_song_keys: set[str],
    tracks_per_review_id: dict[int, int],
    albums_used: set[int],
    spread_limits: AlbumSpreadLimits | None,
) -> int | None:
    """Next cyclic pool index that still has spread capacity and an unused track."""
    n = len(reviews)
    if n <= 1:
        return None
    for step in range(1, n):
        idx = (after_index + step) % n
        if idx in skip_indices:
            continue
        review = reviews[idx]
        if not _album_can_accept_more(
            review,
            album_idx=idx,
            tracks_per_review_id=tracks_per_review_id,
            albums_used=albums_used,
            spread_limits=spread_limits,
        ):
            continue
        if review_has_unused_track_candidate(review, picked_song_keys):
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
    """Pick one track title; returns ``(track_title, source_kind)``."""
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


def _build_slot_album_indices_and_plans(
    *,
    weights: list[float],
    target_count: int,
    rng: random.Random,
    selection_strategy: SelectionStrategy,
) -> tuple[list[int], list[StratifiedSlotPlan]]:
    """Plan one album index per slot plus per-album stratified metadata."""
    n = len(weights)
    if selection_strategy == "stratified":
        plans = build_stratified_slot_plans(weights, target_count)
        slots: list[int] = []
        for album_idx, plan in enumerate(plans):
            slots.extend([album_idx] * plan.quota)
        rng.shuffle(slots)
        return slots, plans

    sampled_slots = weighted_sample_album_indices_without_replacement(
        weights,
        target_count,
        rng,
    )
    rng.shuffle(sampled_slots)
    total_w = float(sum(max(0.0, float(w)) for w in weights))
    quotas_by_album: dict[int, int] = {}
    for idx in sampled_slots:
        quotas_by_album[idx] = quotas_by_album.get(idx, 0) + 1
    plans_out: list[StratifiedSlotPlan] = []
    for i in range(n):
        quota = quotas_by_album.get(i, 0)
        if total_w > 0.0:
            ideal = float(target_count) * float(weights[i]) / total_w
        else:
            ideal = float(target_count) / float(n) if n else 0.0
        plans_out.append(
            StratifiedSlotPlan(
                ideal_slots=ideal,
                floor_slots=quota,
                remainder_extra_slots=0,
                quota=quota,
            ),
        )
    return sampled_slots, plans_out


def build_playlist_suggestions(
    *,
    reviews: list[Review],
    weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    max_attempt_factor: int = 20,
    selection_strategy: SelectionStrategy = "stratified",
    album_spread_mode: AlbumSpreadMode | None = None,
) -> list[PlaylistSuggestion]:
    """Generate playlist suggestions with the requested album-selection strategy."""
    if not reviews or not weights or not raw_scores or target_count <= 0:
        LOGGER.info(
            "Playlist suggestion build skipped: empty inputs "
            "reviews=%s weights=%s raw_scores=%s target_count=%s",
            len(reviews),
            len(weights),
            len(raw_scores),
            target_count,
        )
        return []

    if len(reviews) != len(weights) or len(reviews) != len(raw_scores):
        LOGGER.warning(
            "Playlist suggestion build skipped: parallel list length mismatch "
            "reviews=%s weights=%s raw_scores=%s",
            len(reviews),
            len(weights),
            len(raw_scores),
        )
        return []

    results: list[PlaylistSuggestion] = []
    picked_song_keys: set[str] = set()
    tracks_per_review_id: dict[int, int] = {}
    albums_used: set[int] = set()
    spread_limits = None
    if album_spread_mode is not None:
        base_limits = album_spread_limits(album_spread_mode, target_count=target_count)
        graduated_caps = build_graduated_caps_by_pool_index(album_spread_mode, weights)
        spread_limits = AlbumSpreadLimits(
            max_tracks_per_album=base_limits.max_tracks_per_album,
            caps_by_pool_index=graduated_caps,
        )
    score_weight_by_id = {
        int(r.id): float(w) for r, w in zip(reviews, weights, strict=True)
    }

    skip_no_track = 0
    skip_abandoned_slots = 0
    skip_spread_limit = 0
    slot_album_fallbacks = 0

    slot_album_indices, strat_plans = _build_slot_album_indices_and_plans(
        weights=weights,
        target_count=target_count,
        rng=rng,
        selection_strategy=selection_strategy,
    )
    if spread_limits is not None:
        strat_plans = _cap_stratified_slot_plans(
            strat_plans,
            spread_limits.max_tracks_per_album,
            spread_limits.caps_by_pool_index,
        )
        slot_album_indices = []
        for album_idx, plan in enumerate(strat_plans):
            slot_album_indices.extend([album_idx] * plan.quota)
        rng.shuffle(slot_album_indices)

    pending_slots: deque[int] = deque(slot_album_indices)
    dead_albums_for_slot: set[int] = set()

    max_attempts = max(target_count * max_attempt_factor, target_count)
    attempts = 0
    LOGGER.info(
        "Playlist suggestion build start strategy=%s target_count=%s pool_albums=%s "
        "n_slots=%s max_attempts=%s spread_mode=%s",
        selection_strategy,
        target_count,
        len(reviews),
        len(slot_album_indices),
        max_attempts,
        album_spread_mode,
    )

    def _abandon_current_slot(*, reason: str, **details: object) -> None:
        nonlocal skip_abandoned_slots
        pending_slots.popleft()
        skip_abandoned_slots += 1
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
        nonlocal slot_album_fallbacks
        dead_albums_for_slot.add(album_idx)
        nxt = next_album_index_with_capacity_cyclic(
            reviews,
            after_index=album_idx,
            skip_indices=dead_albums_for_slot,
            picked_song_keys=picked_song_keys,
            tracks_per_review_id=tracks_per_review_id,
            albums_used=albums_used,
            spread_limits=spread_limits,
        )
        if nxt is None:
            return False
        pending_slots[0] = nxt
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
        if not _album_can_accept_more(
            review,
            album_idx=album_idx,
            tracks_per_review_id=tracks_per_review_id,
            albums_used=albums_used,
            spread_limits=spread_limits,
        ):
            skip_spread_limit += 1
            if _try_assign_next_album_for_slot():
                continue
            _abandon_current_slot(
                reason="album_spread_limit_reached",
                review_id=int(review.id),
            )
            continue
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
        key = catalog_lookup_key(review.artist, track_title)
        picked_song_keys.add(key)
        pending_slots.popleft()
        dead_albums_for_slot.clear()
        review_id = int(review.id)
        tracks_per_review_id[review_id] = tracks_per_review_id.get(review_id, 0) + 1
        albums_used.add(review_id)
        plan = strat_plans[album_idx]
        results.append(
            PlaylistSuggestion(
                review_id=review_id,
                artist=review.artist,
                album=review.album,
                track_title=track_title,
                source_kind=source_kind,
                score_weight=score_weight_by_id.get(review_id, 0.0),
                raw_score=float(raw_scores[album_idx]),
                playlist_slot_quota=int(plan.quota),
                strat_ideal_slots=float(plan.ideal_slots),
                strat_floor_slots=int(plan.floor_slots),
                strat_remainder_extra_slots=int(plan.remainder_extra_slots),
                release_year=review.release_year,
                label=primary_review_label(review),
            ),
        )

    if pending_slots:
        LOGGER.warning(
            "Playlist suggestion build hit global attempt limit: "
            "unfilled_slots=%s filled=%s target=%s attempts_used=%s "
            "album_fallbacks=%s abandoned_slots=%s skip_no_track=%s "
            "skip_spread_limit=%s",
            len(pending_slots),
            len(results),
            target_count,
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_spread_limit,
        )
    elif len(results) < target_count:
        LOGGER.warning(
            "Playlist suggestion build stopped early: filled=%s target=%s "
            "attempts_used=%s album_fallbacks=%s abandoned_slots=%s "
            "skip_no_track=%s skip_spread_limit=%s",
            len(results),
            target_count,
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_spread_limit,
        )
    else:
        LOGGER.info(
            "Playlist suggestion build complete: filled=%s attempts_used=%s "
            "album_fallbacks=%s abandoned_slots=%s skip_no_track=%s "
            "skip_spread_limit=%s",
            len(results),
            attempts,
            slot_album_fallbacks,
            skip_abandoned_slots,
            skip_no_track,
            skip_spread_limit,
        )
    return results
