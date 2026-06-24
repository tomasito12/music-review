"""Smoke-test the local Plattenradar API against real project data."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping
from typing import Any

import httpx

from music_review.data_access.communities import load_communities_res_10

LOGGER = logging.getLogger("music_review.api_smoke_test")


def main() -> None:
    """Run a small end-to-end check against a running local API server."""
    args = _parse_args()
    _configure_logging(args.verbose)
    community_id = args.community_id or _first_local_community_id()
    if not community_id:
        raise SystemExit(
            "No local community id found. Run graph-build first or pass "
            "--community-id explicitly.",
        )
    LOGGER.info("Using community_id=%s", community_id)
    profile = _profile_payload(community_id)
    with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
        _check_health(client)
        _check_presets(client)
        _check_archive_recommendations(client, profile)
        _check_new_review_recommendations(client, profile)
        _check_playlist_export(client, profile)
    LOGGER.info("API smoke test completed successfully")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the smoke test."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running API server.",
    )
    parser.add_argument(
        "--community-id",
        default=None,
        help="Community id to use in the temporary taste profile.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def _configure_logging(verbose: bool) -> None:
    """Configure console logging for progress and diagnostics."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _first_local_community_id() -> str | None:
    """Return the first known local resolution-10 community id."""
    for community in load_communities_res_10():
        community_id = community.get("id")
        if community_id:
            return str(community_id)
    return None


def _profile_payload(community_id: str) -> dict[str, object]:
    """Build a minimal temporary taste profile for API checks."""
    return {
        "selected_communities": [community_id],
        "community_weights_raw": {community_id: 1.0},
        "filter_settings": {
            "rating_min": 6.0,
            "rating_max": 10.0,
            "score_min": 0.0,
            "score_max": 1.0,
            "sort_mode": "deterministic",
            "serendipity": 0.0,
        },
    }


def _check_health(client: httpx.Client) -> None:
    """Check the health endpoint."""
    payload = _get_json(client, "/health")
    if payload.get("status") != "ok":
        msg = f"Unexpected health response: {payload!r}"
        raise RuntimeError(msg)
    LOGGER.info("Health endpoint ok")


def _check_presets(client: httpx.Client) -> None:
    """Check the preset endpoint."""
    response = client.get("/v1/presets")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        msg = f"Expected non-empty presets list, got: {payload!r}"
        raise RuntimeError(msg)
    LOGGER.info("Presets endpoint ok n_presets=%s", len(payload))


def _check_archive_recommendations(
    client: httpx.Client,
    profile: Mapping[str, object],
) -> None:
    """Check archive recommendations with a temporary profile."""
    payload = _post_json(
        client,
        "/v1/recommendations/archive",
        {
            "profile": profile,
            "limit": 5,
            "offset": 0,
        },
    )
    _assert_recommendation_set(payload, expected_source="archive")
    _assert_frontend_card_fields(payload, endpoint_name="archive")
    LOGGER.info(
        "Archive recommendations ok total=%s returned=%s",
        payload["total"],
        len(payload["items"]),
    )


def _check_new_review_recommendations(
    client: httpx.Client,
    profile: Mapping[str, object],
) -> None:
    """Check newest-review recommendations with a temporary profile."""
    payload = _post_json(
        client,
        "/v1/recommendations/new-reviews",
        {
            "profile": profile,
            "newest_count": 20,
            "limit": 5,
            "offset": 0,
        },
    )
    _assert_recommendation_set(payload, expected_source="new_reviews")
    _assert_frontend_card_fields(payload, endpoint_name="new_reviews")
    LOGGER.info(
        "New-review recommendations ok total=%s returned=%s",
        payload["total"],
        len(payload["items"]),
    )


def _check_playlist_export(
    client: httpx.Client,
    profile: Mapping[str, object],
) -> None:
    """Check synchronous TuneMyMusic export generation."""
    payload = _post_json(
        client,
        "/v1/playlists/export",
        {
            "source": "new_reviews",
            "profile": profile,
            "playlist_name": "Plattenradar Smoke Test",
            "target_count": 10,
            "taste_exponent": 1.0,
            "selection_strategy": "stratified",
            "format": "txt",
            "newest_count": 20,
        },
    )
    if payload.get("source") != "new_reviews":
        msg = f"Unexpected playlist source: {payload!r}"
        raise RuntimeError(msg)
    if payload.get("content_type") != "text/plain":
        msg = f"Unexpected playlist content type: {payload!r}"
        raise RuntimeError(msg)
    if not isinstance(payload.get("items"), list):
        msg = f"Expected playlist items list: {payload!r}"
        raise RuntimeError(msg)
    for item in payload["items"]:
        if not isinstance(item, dict):
            msg = f"Expected playlist item object: {item!r}"
            raise RuntimeError(msg)
        for key in ("artist", "album", "track_title", "source_kind"):
            if not item.get(key):
                msg = f"Playlist item missing {key}: {item!r}"
                raise RuntimeError(msg)
    LOGGER.info(
        "Playlist export ok filename=%s n_items=%s",
        payload.get("filename"),
        len(payload["items"]),
    )


def _get_json(client: httpx.Client, path: str) -> dict[str, Any]:
    """GET a JSON object from the API."""
    response = client.get(path)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"Expected JSON object from {path}, got: {payload!r}"
        raise RuntimeError(msg)
    return payload


def _post_json(
    client: httpx.Client,
    path: str,
    body: Mapping[str, object],
) -> dict[str, Any]:
    """POST a JSON object and return a JSON object."""
    response = client.post(path, json=body)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"Expected JSON object from {path}, got: {payload!r}"
        raise RuntimeError(msg)
    return payload


def _assert_recommendation_set(
    payload: Mapping[str, Any],
    *,
    expected_source: str,
) -> None:
    """Validate the high-level recommendation response shape."""
    if payload.get("source") != expected_source:
        msg = f"Unexpected source for {expected_source}: {payload!r}"
        raise RuntimeError(msg)
    if not isinstance(payload.get("total"), int):
        msg = f"Recommendation response missing integer total: {payload!r}"
        raise RuntimeError(msg)
    if not isinstance(payload.get("items"), list):
        msg = f"Recommendation response missing items list: {payload!r}"
        raise RuntimeError(msg)


def _assert_frontend_card_fields(
    payload: Mapping[str, Any],
    *,
    endpoint_name: str,
) -> None:
    """Validate fields a frontend recommendation card needs."""
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        LOGGER.warning("%s returned no card items to inspect", endpoint_name)
        return
    first = items[0]
    if not isinstance(first, dict):
        msg = f"{endpoint_name} item is not an object: {first!r}"
        raise RuntimeError(msg)
    required_keys = (
        "artist",
        "album",
        "score_display",
        "playlist_available",
        "has_tracks",
        "matched_tags",
        "explanation_signals",
    )
    missing = [key for key in required_keys if key not in first]
    if missing:
        msg = f"{endpoint_name} card missing keys {missing}: {first!r}"
        raise RuntimeError(msg)
    if not isinstance(first["matched_tags"], list):
        msg = f"{endpoint_name} matched_tags is not a list: {first!r}"
        raise RuntimeError(msg)
    if not isinstance(first["playlist_available"], bool):
        msg = f"{endpoint_name} playlist_available is not bool: {first!r}"
        raise RuntimeError(msg)


if __name__ == "__main__":
    main()
