"""Wikidata client helpers for artist image resolution."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, cast

import requests

from music_review.pipeline.enrichment.wikimedia_http import WIKIMEDIA_HEADERS

logger = logging.getLogger(__name__)

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
_RATE_LIMIT_SECONDS = 0.5
_last_call_ts: float | None = None


def fetch_wikidata_id_by_musicbrainz_mbid(mbid: str) -> str | None:
    """Resolve a Wikidata Q-ID from a MusicBrainz artist MBID."""
    query = (
        "SELECT ?item WHERE { "
        "{ ?item wdt:P435 "
        f'"{mbid}" . }} UNION {{ ?item wdt:P434 "{mbid}" . }} '
        "}"
    )
    bindings = _run_sparql(query)
    for binding in bindings:
        item = binding.get("item")
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if isinstance(value, str):
            wikidata_id = _normalize_wikidata_id(value)
            if wikidata_id is not None:
                return wikidata_id
    return None


def fetch_commons_filename(wikidata_id: str) -> str | None:
    """Return the Commons filename from Wikidata property P18."""
    entity = _fetch_entity(wikidata_id)
    if entity is None:
        return None
    return extract_p18_filename(entity)


def extract_p18_filename(entity: dict[str, Any]) -> str | None:
    """Extract the P18 image filename from one Wikidata entity payload."""
    claims = entity.get("claims")
    if not isinstance(claims, dict):
        return None
    image_claims = claims.get("P18")
    if not isinstance(image_claims, list) or not image_claims:
        return None

    for claim in image_claims:
        if not isinstance(claim, dict):
            continue
        mainsnak = claim.get("mainsnak")
        if not isinstance(mainsnak, dict):
            continue
        datavalue = mainsnak.get("datavalue")
        if not isinstance(datavalue, dict):
            continue
        value = datavalue.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _fetch_entity(wikidata_id: str) -> dict[str, Any] | None:
    """Fetch one Wikidata entity by Q-ID."""
    normalized_id = _normalize_wikidata_id(wikidata_id)
    if normalized_id is None:
        return None

    params = {
        "action": "wbgetentities",
        "ids": normalized_id,
        "props": "claims",
        "format": "json",
    }
    try:
        payload = _get(params)
    except requests.RequestException as exc:
        logger.warning("Wikidata lookup failed for %s: %s", normalized_id, exc)
        return None

    entities = payload.get("entities")
    if not isinstance(entities, dict):
        return None
    entity = entities.get(normalized_id)
    if not isinstance(entity, dict):
        return None
    if entity.get("missing") == "":
        logger.info("Wikidata entity missing for %s", normalized_id)
        return None
    return entity


def _normalize_wikidata_id(value: str) -> str | None:
    """Normalize a Wikidata ID or URL to ``Q123`` form."""
    text = value.strip()
    if not text:
        return None
    match = re.search(r"(Q\d+)", text, flags=re.IGNORECASE)
    if match is None:
        return None
    return f"Q{match.group(1)[1:]}"


def _get(params: dict[str, str]) -> dict[str, Any]:
    """Perform one rate-limited Wikidata API GET request."""
    global _last_call_ts

    if _last_call_ts is not None:
        elapsed = time.time() - _last_call_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)

    response = requests.get(
        WIKIDATA_API_URL,
        headers=WIKIMEDIA_HEADERS,
        params=params,
        timeout=15,
    )
    _last_call_ts = time.time()
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


def _run_sparql(query: str) -> list[dict[str, Any]]:
    """Run one Wikidata SPARQL query and return result bindings."""
    global _last_call_ts

    if _last_call_ts is not None:
        elapsed = time.time() - _last_call_ts
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)

    response = requests.get(
        WIKIDATA_SPARQL_URL,
        headers={
            **WIKIMEDIA_HEADERS,
            "Accept": "application/sparql-results+json",
        },
        params={"query": query},
        timeout=20,
    )
    _last_call_ts = time.time()
    response.raise_for_status()
    payload = cast(dict[str, Any], response.json())
    results = payload.get("results")
    if not isinstance(results, dict):
        return []
    bindings = results.get("bindings")
    if not isinstance(bindings, list):
        return []
    return [item for item in bindings if isinstance(item, dict)]
