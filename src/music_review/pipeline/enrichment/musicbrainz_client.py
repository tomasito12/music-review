"""
Thin wrapper around the MusicBrainz API for fetching tags/genres for albums.

This module uses the `musicbrainzngs` library under the hood:
    pip install musicbrainzngs

You *must* set a sensible USER_AGENT_* configuration before using this module.
"""

from __future__ import annotations

import logging
import random
import re
import time
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from os import getenv
from typing import Any, cast

import requests
from urllib3.exceptions import InsecureRequestWarning

from music_review.pipeline.enrichment.commons_artist_match import (
    musicbrainz_name_matches_requested,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://musicbrainz.org/ws/2"

# Basic User-Agent configuration (can be overridden via env)
USER_AGENT_APP = getenv("USER_AGENT_APP", "music-review")
USER_AGENT_VERSION = getenv("USER_AGENT_VERSION", "0.1.0")
USER_AGENT_CONTACT = getenv("USER_AGENT_CONTACT", "mailto:you@example.com")

HEADERS = {
    "User-Agent": f"{USER_AGENT_APP}/{USER_AGENT_VERSION} ({USER_AGENT_CONTACT})",
}

# Toggle TLS verification via env:
#   MB_VERIFY_TLS=true  (default, sicher)
#   MB_VERIFY_TLS=false (nur lokal, mit Vorsicht!)
MB_VERIFY_TLS = getenv("MB_VERIFY_TLS", "true").lower() == "true"

if not MB_VERIFY_TLS:
    # Suppress only this specific warning when we *intentionally* skip verification
    warnings.filterwarnings("ignore", category=InsecureRequestWarning)
    logger.warning(
        "MusicBrainz TLS verification is DISABLED (MB_VERIFY_TLS=false). "
        "Do not use this setting in production."
    )

_RATE_LIMIT_SECONDS = 1.0
_MAX_RETRIES = 3
_RETRYABLE_HTTP_STATUSES = frozenset({429, 503})
_last_call_ts: float | None = None


@dataclass(slots=True)
class ArtistInfo:
    mbid: str
    name: str
    country: str | None
    artist_type: str | None
    disambiguation: str | None
    tags: list[str]
    members: list[str]


def fetch_artist_info_by_mbid(mbid: str) -> ArtistInfo | None:
    """Lookup a MusicBrainz artist by MBID and return normalized info."""
    trimmed_mbid = mbid.strip()
    if not trimmed_mbid:
        return None

    detailed = _lookup_artist_with_tags(trimmed_mbid)
    if detailed is None:
        return None

    artist_name = detailed.get("name")
    country = detailed.get("country")
    artist_type = detailed.get("type")
    disambiguation = detailed.get("disambiguation")
    resolved_name = (
        str(artist_name)
        if isinstance(artist_name, str) and artist_name.strip()
        else trimmed_mbid
    )
    return ArtistInfo(
        mbid=trimmed_mbid,
        name=resolved_name,
        country=str(country) if isinstance(country, str) else None,
        artist_type=str(artist_type) if isinstance(artist_type, str) else None,
        disambiguation=str(disambiguation) if isinstance(disambiguation, str) else None,
        tags=_extract_tag_names(detailed),
        members=_extract_band_members(detailed),
    )


def fetch_artist_info(name: str) -> ArtistInfo | None:
    """Best-effort lookup of a MusicBrainz artist by human-readable name.

    Steps:
        1) Search artist by name
        2) Select best match (highest score)
        3) Lookup artist by MBID including tags & relations
        4) Return normalized ArtistInfo
    """
    candidates, search_failed = _search_artists(name=name, limit=5)
    if search_failed:
        return None

    best = _select_best_artist(candidates, preferred_name=name)

    if best is None:
        logger.info("No MusicBrainz artist found for name=%s", name)
        return None

    mbid = best["id"]
    artist_name = best.get("name", name)
    country = best.get("country")
    artist_type = best.get("type")
    disambiguation = best.get("disambiguation")

    detailed = _lookup_artist_with_tags(mbid)
    if detailed is None:
        tags: list[str] = []
        members: list[str] = []
    else:
        tags = _extract_tag_names(detailed)
        members = _extract_band_members(detailed)

    logger.debug(
        "Fetched artist info for %s "
        "(mbid=%s, country=%s, type=%s, tags=%d, members=%d)",
        artist_name,
        mbid,
        country,
        artist_type,
        len(tags),
        len(members),
    )

    if not _validate_resolved_artist_name(name, artist_name):
        return None

    return ArtistInfo(
        mbid=mbid,
        name=artist_name,
        country=country,
        artist_type=artist_type,
        disambiguation=disambiguation,
        tags=tags,
        members=members,
    )


def _validate_resolved_artist_name(
    requested_name: str,
    resolved_name: str,
) -> bool:
    """Return whether a MusicBrainz artist name matches the requested lookup name."""
    if musicbrainz_name_matches_requested(requested_name, resolved_name):
        return True
    logger.info(
        "Rejected MusicBrainz artist %s for requested name %s",
        resolved_name,
        requested_name,
    )
    return False


def _search_artists(name: str, limit: int = 5) -> tuple[list[dict[str, Any]], bool]:
    """Search MusicBrainz artists by name.

    Returns a tuple of (candidates, search_failed).
    """
    params = {
        "query": name,
        "fmt": "json",
        "limit": limit,
    }

    try:
        data = _get("/artist", params)
    except requests.RequestException as exc:
        logger.warning("MusicBrainz artist search failed for %s: %s", name, exc)
        return [], True

    return list(data.get("artists", [])), False


def _select_best_artist(
    candidates: Iterable[dict[str, Any]],
    *,
    preferred_name: str | None = None,
) -> dict[str, Any] | None:
    """Pick the most likely artist candidate from a search result list."""
    artists = list(candidates)
    if not artists:
        return None

    if preferred_name:
        preferred = preferred_name.casefold().strip()
        exact_matches = [
            artist
            for artist in artists
            if str(artist.get("name", "")).casefold().strip() == preferred
        ]
        if exact_matches:
            artists = exact_matches

    # Prefer highest MusicBrainz score if present
    def score(a: dict[str, Any]) -> int:
        try:
            return int(a.get("score", 0))
        except (TypeError, ValueError):
            return 0

    artists.sort(key=score, reverse=True)

    return artists[0]


def extract_artist_mbid_from_release_group(
    release_group: dict[str, Any],
) -> str | None:
    """Extract the credited artist MBID from one release-group search hit."""
    credits = release_group.get("artist-credit")
    if not isinstance(credits, list) or not credits:
        return None

    first_credit = credits[0]
    if not isinstance(first_credit, dict):
        return None

    artist = first_credit.get("artist")
    if not isinstance(artist, dict):
        return None

    artist_id = artist.get("id")
    if isinstance(artist_id, str) and artist_id.strip():
        return artist_id.strip()
    return None


def extract_artist_name_from_release_group(
    release_group: dict[str, Any],
) -> str | None:
    """Extract the credited artist name from one release-group search hit."""
    credits = release_group.get("artist-credit")
    if not isinstance(credits, list) or not credits:
        return None

    first_credit = credits[0]
    if not isinstance(first_credit, dict):
        return None

    credit_name = first_credit.get("name")
    if isinstance(credit_name, str) and credit_name.strip():
        return credit_name.strip()

    artist = first_credit.get("artist")
    if isinstance(artist, dict):
        artist_name = artist.get("name")
        if isinstance(artist_name, str) and artist_name.strip():
            return artist_name.strip()
    return None


def _extract_band_members(entity: dict[str, Any]) -> list[str]:
    """Extract band member names from a MusicBrainz artist JSON dict."""
    names: set[str] = set()

    for rel in entity.get("relations", []):
        if rel.get("type") != "member of band":
            continue
        if rel.get("target-type") != "artist":
            continue

        direction = rel.get("direction")
        # For a band entity, relations to members are typically 'backward'
        if direction and direction != "backward":
            continue

        artist = rel.get("artist") or {}
        name = artist.get("name")
        if not name:
            continue

        names.add(name)

    return sorted(names)


@dataclass(slots=True)
class ExternalGenreInfo:
    """Raw genre/tag info fetched from MusicBrainz."""

    mbid: str
    title: str
    artist: str
    tags: list[str]
    artist_mbid: str | None = None
    source: str = "musicbrainz"


def _sleep_if_needed() -> None:
    global _last_call_ts

    if _last_call_ts is None:
        return

    elapsed = time.time() - _last_call_ts
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """Perform one rate-limited MusicBrainz GET request with transient retries."""
    global _last_call_ts

    url = f"{BASE_URL}{path}"
    last_error: requests.RequestException | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        _sleep_if_needed()
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=10,
                verify=MB_VERIFY_TLS,
            )
            _last_call_ts = time.time()
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
        except requests.HTTPError as exc:
            _last_call_ts = time.time()
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code in _RETRYABLE_HTTP_STATUSES and attempt < _MAX_RETRIES:
                last_error = exc
                logger.warning(
                    "MusicBrainz request failed for %s (attempt %d/%d): %s",
                    path,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                _sleep_backoff(attempt)
                continue
            raise
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt < _MAX_RETRIES:
                logger.warning(
                    "MusicBrainz request failed for %s (attempt %d/%d): %s",
                    path,
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                _sleep_backoff(attempt)
                continue
            raise

    if last_error is not None:
        raise last_error
    msg = "MusicBrainz request failed without a captured error"
    raise RuntimeError(msg)


def _sleep_backoff(attempt: int) -> None:
    """Sleep briefly before retrying a transient MusicBrainz request."""
    base = 0.5
    max_sleep = 5.0
    delay = min(max_sleep, base * (2 ** (attempt - 1)))
    jitter = random.uniform(0.0, 0.25 * delay)
    time.sleep(delay + jitter)


def _normalize_search_phrase(value: str) -> str:
    """Normalize artist/album text before building MusicBrainz search queries."""
    text = value.strip()
    text = re.sub(r"\.{2,}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _album_title_search_variants(album: str) -> list[str]:
    """Return album-title variants worth trying against MusicBrainz."""
    variants: list[str] = []
    base = _normalize_search_phrase(album)
    if base:
        variants.append(base)

    without_parenthetical = re.sub(r"\s*\([^)]*\)", "", base).strip()
    if without_parenthetical and without_parenthetical not in variants:
        variants.append(without_parenthetical)

    if ":" in base:
        before_colon = base.split(":", 1)[0].strip()
        if before_colon and before_colon not in variants:
            variants.append(before_colon)

    if " - " in base:
        before_dash = base.split(" - ", 1)[0].strip()
        if before_dash and before_dash not in variants:
            variants.append(before_dash)

    return variants


def _search_release_groups_query(query: str, limit: int) -> list[dict[str, Any]]:
    """Run one MusicBrainz release-group search query."""
    params = {
        "query": query,
        "fmt": "json",
        "limit": limit,
    }

    try:
        data = _get("/release-group", params)
    except requests.RequestException as exc:
        logger.warning(
            "MusicBrainz search failed for query=%s: %s",
            query,
            exc,
        )
        return []

    return list(data.get("release-groups", []))


def search_release_groups(
    artist: str,
    album: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search MusicBrainz release-groups by artist + album name."""
    seen_ids: set[str] = set()
    collected: list[dict[str, Any]] = []

    def add_groups(groups: Iterable[dict[str, Any]]) -> None:
        for group in groups:
            group_id = group.get("id")
            if not isinstance(group_id, str) or not group_id.strip():
                continue
            if group_id in seen_ids:
                continue
            seen_ids.add(group_id)
            collected.append(group)

    for album_variant in _album_title_search_variants(album):
        query = f'artist:"{artist}" AND release:"{album_variant}"'
        add_groups(_search_release_groups_query(query, limit=limit))
        if collected:
            return collected[:limit]

    for album_variant in _album_title_search_variants(album):
        add_groups(
            _search_release_groups_query(
                f'release:"{album_variant}"',
                limit=limit * 2,
            ),
        )
        if collected:
            return collected[:limit]

    return collected[:limit]


def _lookup_release_group_with_tags(mbid: str) -> dict[str, Any] | None:
    """Lookup a release-group by MBID and include tag information."""
    params = {
        "fmt": "json",
        "inc": "tags",
    }

    try:
        data = _get(f"/release-group/{mbid}", params)
    except requests.RequestException as exc:
        logger.warning("MusicBrainz lookup failed for mbid=%s: %s", mbid, exc)
        return None

    return data


def _select_best_release_group(
    release_groups: Iterable[dict[str, Any]],
    *,
    preferred_artist: str | None = None,
) -> dict[str, Any] | None:
    """Pick the most likely album candidate for one review artist/album pair."""
    groups = list(release_groups)
    if not groups:
        return None

    def rank(release_group: dict[str, Any]) -> tuple[int, int, int]:
        is_album = 1 if release_group.get("primary-type", "").lower() == "album" else 0
        artist_match = 0
        if preferred_artist:
            credit_name = extract_artist_name_from_release_group(release_group) or ""
            if musicbrainz_name_matches_requested(preferred_artist, credit_name):
                artist_match = 2
        try:
            score = int(release_group.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        return (artist_match, is_album, score)

    groups.sort(key=rank, reverse=True)
    return groups[0]


def _release_group_artist_mbid(
    release_group: dict[str, Any],
    *,
    preferred_artist: str,
) -> str | None:
    """Return the credited artist MBID when the credit matches the review artist."""
    credit_name = extract_artist_name_from_release_group(release_group) or ""
    if not _validate_resolved_artist_name(preferred_artist, credit_name):
        return None
    return extract_artist_mbid_from_release_group(release_group)


def fetch_artist_alias_names(mbid: str) -> list[str]:
    """Return alias names for one MusicBrainz artist MBID."""
    detailed = _lookup_artist_with_tags(mbid)
    if detailed is None:
        return []

    names: list[str] = []
    for alias in detailed.get("aliases", []):
        if not isinstance(alias, dict):
            continue
        alias_name = alias.get("name")
        if isinstance(alias_name, str) and alias_name.strip():
            names.append(alias_name.strip())
    return names


def fetch_artist_disambiguation(mbid: str) -> str | None:
    """Return the MusicBrainz disambiguation comment for one artist MBID."""
    detailed = _lookup_artist_with_tags(mbid)
    if detailed is None:
        return None
    disambiguation = detailed.get("disambiguation")
    if isinstance(disambiguation, str) and disambiguation.strip():
        return disambiguation.strip()
    return None


def fetch_artist_wikidata_id(mbid: str) -> str | None:
    """Return the Wikidata Q-ID linked from a MusicBrainz artist MBID."""
    params = {
        "fmt": "json",
        "inc": "url-rels",
    }
    try:
        data = _get(f"/artist/{mbid}", params)
    except Exception as exc:
        logger.warning(
            "MusicBrainz artist url-rel lookup failed for mbid=%s: %s",
            mbid,
            exc,
        )
        return None
    return extract_wikidata_id_from_artist(data)


def extract_wikidata_id_from_artist(artist: dict[str, Any]) -> str | None:
    """Extract a Wikidata Q-ID from a MusicBrainz artist JSON object."""
    for rel in artist.get("relations", []):
        if not isinstance(rel, dict):
            continue
        if rel.get("type") != "wikidata":
            continue
        resource = _relation_url_resource(rel.get("url"))
        wikidata_id = _wikidata_id_from_resource(resource)
        if wikidata_id is not None:
            return wikidata_id
    return None


def _relation_url_resource(url_field: object) -> str | None:
    """Read the URL resource from one MusicBrainz relation payload."""
    if isinstance(url_field, dict):
        resource = url_field.get("resource")
        if isinstance(resource, str) and resource.strip():
            return resource.strip()
        return None
    if isinstance(url_field, str) and url_field.strip():
        return url_field.strip()
    return None


def _wikidata_id_from_resource(resource: str | None) -> str | None:
    """Extract a Q-ID from a Wikidata URL or bare identifier."""
    if resource is None:
        return None
    match = re.search(r"(Q\d+)", resource, flags=re.IGNORECASE)
    if match is None:
        return None
    return f"Q{match.group(1)[1:]}"


def _lookup_artist_with_tags(mbid: str) -> dict[str, Any] | None:
    """Lookup a MusicBrainz artist by MBID and include tag and relation information."""
    params = {
        "fmt": "json",
        # important: we need artist-rels to get band members
        "inc": "aliases+tags+artist-rels",
    }

    try:
        data = _get(f"/artist/{mbid}", params)
    except Exception as exc:  # requests.RequestException etc.
        logger.warning("MusicBrainz artist lookup failed for mbid=%s: %s", mbid, exc)
        return None

    return data


def _extract_tag_names(release_group: dict[str, Any]) -> list[str]:
    """Extract normalized tag names from a release-group JSON dict."""
    tags: list[str] = []

    # Some endpoints use "tags", older examples "tag-list"
    raw_tags = release_group.get("tags") or release_group.get("tag-list") or []

    for tag in raw_tags:
        name = tag.get("name")
        if not name:
            continue
        tags.append(name.strip().lower())

    return tags


def fetch_album_tags(artist: str, album: str) -> ExternalGenreInfo | None:
    """
    Best-effort lookup of tags for an album (artist + album name).

    1) Search release-groups
    2) Select best candidate
    3) Lookup that release-group with tags
    """
    release_groups = search_release_groups(artist=artist, album=album, limit=5)
    best = _select_best_release_group(release_groups, preferred_artist=artist)
    if best is None:
        logger.info("No release-group found for %s - %s", artist, album)
        return None

    mbid = best["id"]
    title = best.get("title", album)
    credited_artist_name = extract_artist_name_from_release_group(best)
    credited_artist_mbid = _release_group_artist_mbid(
        best,
        preferred_artist=artist,
    )

    detailed = _lookup_release_group_with_tags(mbid)
    if detailed is None:
        logger.info("No detailed release-group found for mbid=%s", mbid)
        return None

    tags = _extract_tag_names(detailed)

    logger.debug(
        "Fetched %d tags for %s - %s (mbid=%s)",
        len(tags),
        artist,
        title,
        mbid,
    )

    return ExternalGenreInfo(
        mbid=mbid,
        title=title,
        artist=credited_artist_name or artist,
        tags=tags,
        artist_mbid=credited_artist_mbid,
    )


# ---------------------------------------------------------------------------
# Optional: simple dict-based tag→genre mapping (legacy/alternative).
# The main metadata pipeline uses genre_regex.py + map_tags_to_genres_regex.
# ---------------------------------------------------------------------------

RAW_TAG_TO_GENRE: dict[str, str] = {
    "indie rock": "indie_rock",
    "indie": "indie_rock",
    "alternative rock": "alternative_rock",
    "alternative": "alternative_rock",
    "electronic": "electronic",
    "electronica": "electronic",
    "hip hop": "hip_hop",
    "hip-hop": "hip_hop",
    "metal": "metal",
    "black metal": "black_metal",
    "death metal": "death_metal",
    "pop": "pop",
    "synthpop": "synth_pop",
    "synth pop": "synth_pop",
    "post-rock": "post_rock",
    "post rock": "post_rock",
    "shoegaze": "shoegaze",
    "dream pop": "dream_pop",
    # extend as needed...
}


def map_tags_to_genres(
    tags: Iterable[str],
    mapping: dict[str, str] | None = None,
) -> list[str]:
    """Map raw MusicBrainz tags to internal canonical genre names."""
    if mapping is None:
        mapping = RAW_TAG_TO_GENRE

    genres: list[str] = []
    for raw in tags:
        key = raw.strip().lower()
        genre = mapping.get(key)
        if genre and genre not in genres:
            genres.append(genre)

    return genres


def fetch_album_genres(artist: str, album: str) -> list[str]:
    """
    Convenience: fetch tags from MusicBrainz and map to internal genres.

    Returns a (possibly empty) list of canonical genre tags.
    """
    info = fetch_album_tags(artist=artist, album=album)
    if info is None:
        return []

    return map_tags_to_genres(info.tags)


if __name__ == "__main__":
    info = fetch_album_tags(artist="The Beatles", album="Abbey Road")
    print(info)
