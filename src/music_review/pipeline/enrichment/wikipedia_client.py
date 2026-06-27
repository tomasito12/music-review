"""English Wikipedia helpers for artist image fallback resolution."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, cast
from urllib.parse import unquote, urlparse

import requests

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.pipeline.enrichment.commons_client import fetch_commons_image_info
from music_review.pipeline.enrichment.wikidata_client import fetch_commons_filename
from music_review.pipeline.enrichment.wikimedia_http import WIKIMEDIA_HEADERS

logger = logging.getLogger(__name__)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
_SEARCH_LIMIT = 5
_RATE_LIMIT_SECONDS = 0.5
_last_call_ts: float | None = None

_MUSIC_SNIPPET_RE = re.compile(
    r"\b(?:band|musician|singer|rapper|group|dj|orchestra|ensemble)\b",
    flags=re.IGNORECASE,
)


def find_commons_image_via_wikipedia(
    search_names: list[str],
    *,
    disambiguation: str | None = None,
) -> tuple[CommonsImageInfo | None, str | None]:
    """Find a licensed Commons image via matching English Wikipedia articles."""
    best: tuple[int, CommonsImageInfo, str | None] | None = None
    seen_titles: set[str] = set()

    for query in _unique_wikipedia_queries(search_names, disambiguation=disambiguation):
        hits = _search_wikipedia(query, limit=_SEARCH_LIMIT)
        for hit in hits:
            title = hit.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            normalized_title = title.strip()
            if normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)

            score = _score_wikipedia_hit(
                hit,
                search_names,
                disambiguation=disambiguation,
            )
            if score < 15:
                continue

            info, wikidata_id = _image_from_wikipedia_title(normalized_title)
            if info is None:
                continue
            if best is None or score > best[0]:
                best = (score, info, wikidata_id)

    if best is None:
        logger.info("Wikipedia search found no usable images for %s", search_names)
        return None, None

    info, wikidata_id = best[1], best[2]
    logger.info(
        "Wikipedia selected %s (score=%d)",
        info.commons_file,
        best[0],
    )
    return info, wikidata_id


def build_wikipedia_search_names(
    artist_name: str,
    *,
    alias_names: list[str] | None = None,
    include_the_variants: bool = True,
) -> list[str]:
    """Build distinct artist name variants for Wikipedia lookup."""
    names: list[str] = []
    seen: set[str] = set()

    def add_name(value: str) -> None:
        text = value.strip()
        if not text:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        names.append(text)

    add_name(artist_name)
    for alias in alias_names or []:
        add_name(alias)

    if include_the_variants:
        for base in list(names):
            if not base.lower().startswith("the "):
                add_name(f"The {base}")
    return names


def _unique_wikipedia_queries(
    search_names: list[str],
    *,
    disambiguation: str | None = None,
) -> list[str]:
    """Build ordered Wikipedia search queries from artist names."""
    queries: list[str] = []
    seen: set[str] = set()

    def add_query(value: str) -> None:
        text = value.strip()
        if not text:
            return
        key = text.casefold()
        if key in seen:
            return
        seen.add(key)
        queries.append(text)

    disambiguation_text = disambiguation.strip() if disambiguation else ""
    for name in search_names:
        if disambiguation_text:
            add_query(f'"{name}" {disambiguation_text}')
            add_query(f"{name} {disambiguation_text}")
        add_query(f'"{name}" band')
        add_query(f"{name} band")
        add_query(f'"{name}"')
        add_query(name)
    return queries


def _image_from_wikipedia_title(
    title: str,
) -> tuple[CommonsImageInfo | None, str | None]:
    """Resolve a Commons image from one Wikipedia article title."""
    page = _fetch_wikipedia_page(title)
    if page is None:
        return None, None

    wikidata_id = _wikidata_id_from_page(page)
    commons_filename = _commons_filename_from_page(page)
    if commons_filename is None and wikidata_id is not None:
        commons_filename = fetch_commons_filename(wikidata_id)
    if commons_filename is None:
        return None, wikidata_id

    info = fetch_commons_image_info(commons_filename)
    return info, wikidata_id


def _fetch_wikipedia_page(title: str) -> dict[str, Any] | None:
    """Fetch page image and Wikidata metadata for one Wikipedia title."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "pageimages|pageprops",
        "piprop": "name|original",
    }
    try:
        payload = _get(params)
    except requests.RequestException as exc:
        logger.warning("Wikipedia lookup failed for %s: %s", title, exc)
        return None

    pages = payload.get("query", {})
    if not isinstance(pages, dict):
        return None
    page_map = pages.get("pages")
    if not isinstance(page_map, dict) or not page_map:
        return None
    page = next(iter(page_map.values()))
    return page if isinstance(page, dict) else None


def _commons_filename_from_page(page: dict[str, Any]) -> str | None:
    """Extract a Commons filename from one Wikipedia page payload."""
    pageprops = page.get("pageprops")
    if isinstance(pageprops, dict):
        image_free = pageprops.get("page_image_free")
        if isinstance(image_free, str) and image_free.strip():
            return image_free.strip().replace("_", " ")

    original = page.get("original")
    if isinstance(original, dict):
        source = original.get("source")
        if isinstance(source, str):
            filename = _commons_filename_from_upload_url(source)
            if filename is not None:
                return filename

    pageimage = page.get("pageimage")
    if isinstance(pageimage, str) and pageimage.strip():
        return pageimage.strip().replace("_", " ")
    return None


def _commons_filename_from_upload_url(url: str) -> str | None:
    """Parse a Commons filename from a Wikimedia upload URL."""
    path = urlparse(url).path
    if "/commons/" not in path:
        return None
    filename = unquote(path.rsplit("/", maxsplit=1)[-1])
    return filename.replace("_", " ") if filename else None


def _wikidata_id_from_page(page: dict[str, Any]) -> str | None:
    """Read the linked Wikidata item from one Wikipedia page."""
    pageprops = page.get("pageprops")
    if not isinstance(pageprops, dict):
        return None
    item = pageprops.get("wikibase_item")
    if isinstance(item, str) and re.fullmatch(r"Q\d+", item, flags=re.IGNORECASE):
        return f"Q{item[1:]}"
    return None


def _search_wikipedia(query: str, *, limit: int) -> list[dict[str, Any]]:
    """Search English Wikipedia and return raw hit dicts."""
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": str(max(1, limit)),
    }
    try:
        payload = _get(params)
    except requests.RequestException as exc:
        logger.warning("Wikipedia search failed for %s: %s", query, exc)
        return []

    query_block = payload.get("query")
    if not isinstance(query_block, dict):
        return []
    results = query_block.get("search")
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, dict)]


def _score_wikipedia_hit(
    hit: dict[str, Any],
    search_names: list[str],
    *,
    disambiguation: str | None = None,
) -> int:
    """Score one Wikipedia search hit for music-artist relevance."""
    title = hit.get("title")
    snippet = hit.get("snippet")
    title_text = title if isinstance(title, str) else ""
    snippet_text = re.sub(r"<[^>]+>", "", snippet) if isinstance(snippet, str) else ""
    combined = f"{title_text} {snippet_text}".casefold()

    score = 0
    if _MUSIC_SNIPPET_RE.search(combined):
        score += 25
    if "disambiguation" in combined:
        score -= 30

    name_tokens = _artist_name_tokens(search_names)
    title_cf = title_text.casefold()
    if name_tokens:
        title_hits = sum(1 for token in name_tokens if token in title_cf)
        if title_hits == 0:
            score -= 40
            if any(token in combined for token in name_tokens):
                score += 25
        elif title_hits == len(name_tokens):
            score += 35
        else:
            score += 15

    for name in search_names:
        normalized = name.strip().casefold()
        if normalized and normalized in combined:
            score += 20
        if normalized and normalized in title_cf:
            score += 25
            break

    if disambiguation:
        hint_tokens = _disambiguation_tokens(disambiguation)
        if hint_tokens:
            matches = sum(1 for token in hint_tokens if token in combined)
            if matches:
                score += matches * 15
            else:
                score -= 45

    return score


def _disambiguation_tokens(disambiguation: str) -> list[str]:
    """Return helpful tokens from a MusicBrainz disambiguation comment."""
    return [
        token
        for token in re.sub(r"[^a-z0-9]+", " ", disambiguation.casefold()).split()
        if len(token) > 3
    ]


def _artist_name_tokens(search_names: list[str]) -> list[str]:
    """Return distinctive tokens shared across artist search names."""
    token_sets = [
        {
            token
            for token in re.sub(r"[^a-z0-9]+", " ", name.casefold()).split()
            if len(token) > 2 and token != "the"
        }
        for name in search_names
        if name.strip()
    ]
    if not token_sets:
        return []
    shared = set.intersection(*token_sets)
    if shared:
        return sorted(shared)
    first = token_sets[0]
    return sorted(first)


def _get(params: dict[str, str]) -> dict[str, Any]:
    """Perform one rate-limited Wikipedia API GET request."""
    global _last_call_ts

    if _last_call_ts is not None:
        elapsed = time.time() - _last_call_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)

    response = requests.get(
        WIKIPEDIA_API_URL,
        headers=WIKIMEDIA_HEADERS,
        params=params,
        timeout=15,
    )
    _last_call_ts = time.time()
    response.raise_for_status()
    return cast(dict[str, Any], response.json())
