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
import random
import re
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


def _norm_text(value: str) -> str:
    clean = _NON_WORD_RE.sub(" ", value.casefold())
    return _SPACE_RE.sub(" ", clean).strip()


def build_album_weights(
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
) -> tuple[list[Review], list[float]]:
    """Return reviews and normalized sampling weights.

    When ``ranked_rows`` is set, the returned list follows **row order** (same as
    the ranked UI), not the order of the ``reviews`` argument. Each weight is
    ``max(0, overall_score) / sum(...)``, so scores ``0.3, 0.1, 0.1`` yield
    sampling probabilities ``3/5, 1/5, 1/5`` on each **independent** weighted
    draw with replacement (see :func:`build_playlist_candidates`).

    Falls back to a uniform distribution when no ranked rows are present or
    when no valid rows remain.
    """
    if not reviews:
        LOGGER.info("Album weights: empty review list")
        return [], []
    if not ranked_rows:
        w = 1.0 / float(len(reviews))
        LOGGER.info(
            "Album weights: uniform (no ranking) pool_size=%s weight_each=%.6f",
            len(reviews),
            w,
        )
        LOGGER.debug(
            "Album weights: uniform mode review_ids_sample=%s",
            [int(r.id) for r in reviews[:8]],
        )
        return reviews, [w for _ in reviews]

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
        LOGGER.warning(
            "Album weights: ranked rows had no valid reviews; uniform fallback "
            "pool_size=%s",
            len(reviews),
        )
        return reviews, [w for _ in reviews]

    total = sum(raw_weights)
    if total <= 0.0:
        w = 1.0 / float(len(picked_reviews))
        LOGGER.warning(
            "Album weights: all scores zero or negative; uniform over %s ranked rows",
            len(picked_reviews),
        )
        return picked_reviews, [w for _ in picked_reviews]
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
    return picked_reviews, norm_weights


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
            key = f"{_norm_text(review.artist)}::{_norm_text(track.title)}"
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
    target_count: int,
    rng: random.Random,
    resolve_fn: ResolveTrackUriFn,
    max_attempt_factor: int = 40,
) -> list[PlaylistCandidate]:
    """Generate playlist candidates using weighted random album sampling.

    Each successful slot: draw one album with ``random.choices(..., weights=weights)``
    (**with replacement**). Then pick a track: random among highlights not yet
    used in the playlist; if none left, random among non-highlights. If Spotify
    resolution fails, the album draw is effectively **re-tried**, so albums with
    more reliable API matches can appear more often in the final list than raw
    weights suggest.
    """
    if not reviews or not weights or target_count <= 0:
        LOGGER.info(
            "Playlist candidate build skipped: empty inputs "
            "reviews=%s weights=%s target_count=%s",
            len(reviews),
            len(weights),
            target_count,
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

    max_attempts = max(target_count * max_attempt_factor, target_count)
    attempts = 0
    LOGGER.info(
        "Playlist candidate build start target_count=%s pool_albums=%s max_attempts=%s",
        target_count,
        len(reviews),
        max_attempts,
    )
    while len(results) < target_count and attempts < max_attempts:
        attempts += 1
        review = rng.choices(reviews, weights=weights, k=1)[0]
        w_album = score_weight_by_id.get(int(review.id), 0.0)
        LOGGER.debug(
            "Playlist draw attempt=%s filled=%s/%s review_id=%s album_weight=%.6f "
            "artist=%r album=%r",
            attempts,
            len(results),
            target_count,
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
            LOGGER.warning(
                "Playlist skip: no unused track review_id=%s artist=%r album=%r "
                "highlights=%s non_highlights=%s tracklist_len=%s",
                review.id,
                _log_str(review.artist),
                _log_str(review.album),
                len(hl),
                len(nh),
                len(review.tracklist),
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
            LOGGER.warning(
                "Playlist skip: resolver returned empty review_id=%s track=%r "
                "(see Spotify strict-resolve logs above)",
                review.id,
                _log_str(track_title, max_len=100),
            )
            continue
        if uri in picked_uris:
            skip_dup_uri += 1
            LOGGER.warning(
                "Playlist skip: duplicate spotify uri review_id=%s uri=%r track=%r",
                review.id,
                _log_str(uri, max_len=80),
                _log_str(track_title, max_len=80),
            )
            continue
        key = f"{_norm_text(review.artist)}::{_norm_text(track_title)}"
        picked_song_keys.add(key)
        picked_uris.add(uri)
        results.append(
            PlaylistCandidate(
                review_id=int(review.id),
                artist=review.artist,
                album=review.album,
                track_title=track_title,
                source_kind=source_kind,
                spotify_uri=uri,
                score_weight=score_weight_by_id.get(int(review.id), 0.0),
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
    if len(results) < target_count:
        LOGGER.warning(
            "Playlist candidate build stopped early: filled=%s target=%s "
            "attempts_used=%s skip_no_track=%s skip_unresolved=%s skip_dup_uri=%s",
            len(results),
            target_count,
            attempts,
            skip_no_track,
            skip_unresolved,
            skip_dup_uri,
        )
    else:
        LOGGER.info(
            "Playlist candidate build complete: filled=%s attempts_used=%s "
            "skip_no_track=%s skip_unresolved=%s skip_dup_uri=%s",
            len(results),
            attempts,
            skip_no_track,
            skip_unresolved,
            skip_dup_uri,
        )
    return results
