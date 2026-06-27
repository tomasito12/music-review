"""Wikimedia Commons client helpers for artist image metadata."""

from __future__ import annotations

import html
import logging
import re
import time
from typing import Any, cast
from urllib.parse import quote

import requests

from music_review.application.artist_image_attribution import (
    build_attribution_text,
    is_license_allowed,
)
from music_review.application.artist_image_models import CommonsImageInfo
from music_review.pipeline.enrichment.wikimedia_http import WIKIMEDIA_HEADERS

logger = logging.getLogger(__name__)

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
_THUMB_WIDTH = 400
_SEARCH_RESULT_LIMIT = 15
_MIN_SEARCH_SCORE = 10
_RATE_LIMIT_SECONDS = 0.5
_last_call_ts: float | None = None

_EXCLUDED_FILENAME_RE = re.compile(
    r"(?:^|[\s_\-])(?:logo|icon|flag|map|chart|diagram|discography|signature|"
    r"locator|ticket|screenshot|music.?video|official.?video|album.?cover|"
    r"single.?cover|war.?memorial)(?:[\s_\-]|$)",
    flags=re.IGNORECASE,
)
_PREFERRED_FILENAME_RE = re.compile(
    r"(live|concert|perform|press|portrait|band|festival|on.?stage|tour)",
    flags=re.IGNORECASE,
)


def find_commons_image_by_artist_name(
    artist_name: str,
    *,
    limit: int = _SEARCH_RESULT_LIMIT,
    thumb_width: int = _THUMB_WIDTH,
) -> CommonsImageInfo | None:
    """Search Commons by artist name and return the best licensed match."""
    name = artist_name.strip()
    if not name:
        return None

    candidates = _search_commons_image_candidates(
        name,
        exact=True,
        limit=limit,
        thumb_width=thumb_width,
    )
    if not candidates:
        candidates = _search_commons_image_candidates(
            name,
            exact=False,
            limit=limit,
            thumb_width=thumb_width,
        )
    if not candidates:
        logger.info("Commons search returned no files for %s", name)
        return None

    ranked = sorted(
        candidates,
        key=lambda item: score_commons_search_candidate(item[0], name),
        reverse=True,
    )
    for title, imageinfo in ranked:
        score = score_commons_search_candidate(title, name)
        if score < _MIN_SEARCH_SCORE:
            continue
        info = parse_commons_image_info(title, imageinfo)
        if info is not None:
            logger.info(
                "Commons search selected %s for %s (score=%d)",
                info.commons_file,
                name,
                score,
            )
            return info

    logger.info("Commons search found files for %s but none passed filters", name)
    return None


def score_commons_search_candidate(commons_title: str, artist_name: str) -> int:
    """Score one Commons search hit for artist-name relevance."""
    normalized_name = _normalize_match_text(artist_name)
    normalized_file = _normalize_match_text(_filename_from_title(commons_title))
    if not normalized_name or not normalized_file:
        return -100

    score = 0
    if normalized_name in normalized_file:
        score += 50

    for token in _name_tokens(normalized_name):
        if token in normalized_file:
            score += 10

    if _EXCLUDED_FILENAME_RE.search(normalized_file.replace(" ", "_")):
        score -= 100
    if _PREFERRED_FILENAME_RE.search(normalized_file):
        score += 5

    return score


def fetch_commons_image_info(
    commons_filename: str,
    *,
    thumb_width: int = _THUMB_WIDTH,
) -> CommonsImageInfo | None:
    """Fetch image URLs and license metadata for one Commons file."""
    title = _commons_file_title(commons_filename)
    payload = _query_image_info(title, thumb_width=thumb_width)
    if payload is None:
        return None
    return parse_commons_image_info(title, payload)


def parse_commons_image_info(
    commons_title: str,
    imageinfo: dict[str, Any],
) -> CommonsImageInfo | None:
    """Parse one Commons ``imageinfo`` block into a structured record."""
    image_url = _optional_str(imageinfo.get("url"))
    thumbnail_url = _optional_str(imageinfo.get("thumburl")) or image_url
    if image_url is None or thumbnail_url is None:
        return None

    metadata = imageinfo.get("extmetadata")
    if not isinstance(metadata, dict):
        return None

    license_name = _metadata_value(metadata, "LicenseShortName")
    if license_name is None or not is_license_allowed(license_name):
        logger.info("Rejected Commons license for %s: %s", commons_title, license_name)
        return None

    author = (
        _metadata_value(metadata, "Artist")
        or _metadata_value(metadata, "Credit")
        or "unbekannt"
    )
    object_name = _metadata_value(metadata, "ObjectName")
    if object_name is None:
        object_name = _title_from_file(commons_title)
    source_url = commons_file_page_url(commons_title)
    license_url = _metadata_value(metadata, "LicenseUrl")

    attribution_text = build_attribution_text(
        title=object_name,
        author=_strip_html(author),
        license_name=license_name,
        source_url=source_url,
    )

    return CommonsImageInfo(
        commons_file=_filename_from_title(commons_title),
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        license=license_name,
        license_url=license_url,
        author=_strip_html(author),
        source_url=source_url,
        attribution_text=attribution_text,
        title=_strip_html(object_name),
    )


def commons_file_page_url(commons_title: str) -> str:
    """Build the Commons file page URL for a file title."""
    normalized = _commons_file_title(commons_title).replace(" ", "_")
    return f"https://commons.wikimedia.org/wiki/{quote(normalized, safe=':/_')}"


def _search_commons_image_candidates(
    artist_name: str,
    *,
    exact: bool,
    limit: int,
    thumb_width: int,
) -> list[tuple[str, dict[str, Any]]]:
    """Return Commons search hits with parsed imageinfo payloads."""
    query = f'"{artist_name}"' if exact else artist_name
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(max(1, limit)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": str(thumb_width),
    }
    try:
        payload = _get(params)
    except requests.RequestException as exc:
        logger.warning("Commons search failed for %s: %s", artist_name, exc)
        return []

    query_block = payload.get("query")
    if not isinstance(query_block, dict):
        return []
    pages = query_block.get("pages")
    if not isinstance(pages, dict) or not pages:
        return []

    candidates: list[tuple[str, dict[str, Any]]] = []
    for page in pages.values():
        if not isinstance(page, dict):
            continue
        title = _optional_str(page.get("title"))
        imageinfo = page.get("imageinfo")
        if title is None or not isinstance(imageinfo, list) or not imageinfo:
            continue
        first = imageinfo[0]
        if isinstance(first, dict):
            candidates.append((title, first))
    return candidates


def _normalize_match_text(value: str) -> str:
    """Normalize text for loose artist/file name matching."""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _name_tokens(normalized_name: str) -> list[str]:
    """Return significant name tokens for matching."""
    return [token for token in normalized_name.split() if len(token) > 2]


def _query_image_info(title: str, *, thumb_width: int) -> dict[str, Any] | None:
    params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "titles": title,
        "iiprop": "url|extmetadata",
        "iiurlwidth": str(thumb_width),
    }
    try:
        payload = _get(params)
    except requests.RequestException as exc:
        logger.warning("Commons lookup failed for %s: %s", title, exc)
        return None

    query = payload.get("query")
    if not isinstance(query, dict):
        return None
    pages = query.get("pages")
    if not isinstance(pages, dict) or not pages:
        return None

    page = next(iter(pages.values()))
    if not isinstance(page, dict):
        return None
    imageinfo = page.get("imageinfo")
    if not isinstance(imageinfo, list) or not imageinfo:
        return None
    first = imageinfo[0]
    if not isinstance(first, dict):
        return None
    return first


def _commons_file_title(filename: str) -> str:
    """Normalize a Commons filename to a ``File:`` title."""
    text = filename.strip().replace(" ", "_")
    if text.lower().startswith("file:"):
        return "File:" + text[5:].lstrip("_")
    return f"File:{text}"


def _filename_from_title(commons_title: str) -> str:
    """Return the bare filename from a Commons title."""
    if commons_title.lower().startswith("file:"):
        return commons_title[5:].replace("_", " ")
    return commons_title.replace("_", " ")


def _title_from_file(commons_title: str) -> str:
    """Derive a human title from a Commons filename."""
    filename = _filename_from_title(commons_title)
    stem = re.sub(r"\.[a-zA-Z0-9]+$", "", filename)
    return stem.replace("_", " ").strip()


def _metadata_value(metadata: dict[str, Any], key: str) -> str | None:
    """Read one extmetadata string value."""
    raw = metadata.get(key)
    if not isinstance(raw, dict):
        return None
    return _optional_str(raw.get("value"))


def _strip_html(value: str) -> str:
    """Remove simple HTML wrappers from Commons metadata strings."""
    without_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(without_tags).strip()


def _optional_str(value: object) -> str | None:
    """Return a stripped string or None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get(params: dict[str, str]) -> dict[str, Any]:
    """Perform one rate-limited Commons API GET request."""
    global _last_call_ts

    if _last_call_ts is not None:
        elapsed = time.time() - _last_call_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)

    response = requests.get(
        COMMONS_API_URL,
        headers=WIKIMEDIA_HEADERS,
        params=params,
        timeout=15,
    )
    _last_call_ts = time.time()
    response.raise_for_status()
    return cast(dict[str, Any], response.json())
