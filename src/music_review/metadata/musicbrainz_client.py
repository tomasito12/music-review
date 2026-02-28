"""
Thin wrapper around the MusicBrainz API for fetching tags/genres for albums.

This module uses the `musicbrainzngs` library under the hood:
    pip install musicbrainzngs

You *must* set a sensible USER_AGENT_* configuration before using this module.
"""

from __future__ import annotations

import logging
import time
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from os import getenv
from typing import Any

import requests
from urllib3.exceptions import InsecureRequestWarning

import music_review.config  # noqa: F401 - load .env early

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


def fetch_artist_info(name: str) -> ArtistInfo | None:
    """Best-effort lookup of a MusicBrainz artist by human-readable name.

    Steps:
        1) Search artist by name
        2) Select best match (highest score)
        3) Lookup artist by MBID including tags & relations
        4) Return normalized ArtistInfo
    """
    candidates = _search_artists(name=name, limit=5)
    best = _select_best_artist(candidates)

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
        "Fetched artist info for %s (mbid=%s, country=%s, type=%s, tags=%d, members=%d)",
        artist_name,
        mbid,
        country,
        artist_type,
        len(tags),
        len(members),
    )

    return ArtistInfo(
        mbid=mbid,
        name=artist_name,
        country=country,
        artist_type=artist_type,
        disambiguation=disambiguation,
        tags=tags,
        members=members,
    )


def _search_artists(name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search MusicBrainz artists by name."""
    params = {
        "query": name,
        "fmt": "json",
        "limit": limit,
    }

    try:
        data = _get("/artist", params)
    except Exception as exc:  # requests.RequestException o.ä. je nach _get-Implementierung
        logger.warning("MusicBrainz artist search failed for %s: %s", name, exc)
        return []

    return list(data.get("artists", []))


def _select_best_artist(candidates: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the most likely artist candidate from a search result list."""
    artists = list(candidates)
    if not artists:
        return None

    # Prefer highest MusicBrainz score if present
    def score(a: dict[str, Any]) -> int:
        try:
            return int(a.get("score", 0))
        except (TypeError, ValueError):
            return 0

    artists.sort(key=score, reverse=True)

    return artists[0]


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
    source: str = "musicbrainz"


def _sleep_if_needed() -> None:
    global _last_call_ts

    if _last_call_ts is None:
        return

    elapsed = time.time() - _last_call_ts
    if elapsed < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - elapsed)


def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    global _last_call_ts

    _sleep_if_needed()
    url = f"{BASE_URL}{path}"

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=10,
    )
    _last_call_ts = time.time()
    response.raise_for_status()
    return response.json()


def search_release_groups(
        artist: str,
        album: str,
        limit: int = 5,
) -> list[dict[str, Any]]:
    """Search MusicBrainz release-groups by artist + album name."""
    params = {
        "query": f'artist:"{artist}" AND release:"{album}"',
        "fmt": "json",
        "limit": limit,
    }

    try:
        data = _get("/release-group", params)
    except requests.RequestException as exc:
        logger.warning(
            "MusicBrainz search failed for %s - %s: %s",
            artist,
            album,
            exc,
        )
        return []

    # note: JSON uses "release-groups" here (not "release-group-list")
    return list(data.get("release-groups", []))


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
) -> dict[str, Any] | None:
    """Pick the most likely album candidate (prefer primary-type Album)."""
    groups = list(release_groups)
    if not groups:
        return None

    albums = [
        rg for rg in groups if rg.get("primary-type", "").lower() == "album"
    ]
    if albums:
        return albums[0]

    return groups[0]


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
    best = _select_best_release_group(release_groups)
    if best is None:
        logger.info("No release-group found for %s - %s", artist, album)
        return None

    mbid = best["id"]
    title = best.get("title", album)

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
        artist=artist,
        tags=tags,
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
