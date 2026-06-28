"""Verify that cached artist images are ready for Aktuell/Entdecken."""

from __future__ import annotations

import argparse
import logging
from typing import Any

import httpx

from music_review.application.artist_image_pipeline_verify import (
    artist_targets_from_recommendation_items,
    check_artist_image_api_readiness,
    sample_lookup_keys_from_cache,
    verify_artist_image_pipeline,
)
from music_review.data_access.communities import load_communities_res_10

LOGGER = logging.getLogger("music_review.verify_artist_image_pipeline")


def _target_mbid(lookup_key: str) -> str:
    """Return the MBID part of a cache lookup key."""
    if lookup_key.startswith("name:"):
        return ""
    return lookup_key


def _targets_from_cache_samples(limit: int) -> list[tuple[str, str, str]]:
    """Build verification targets from local cache samples."""
    return [
        (lookup_key, artist_name, _target_mbid(lookup_key))
        for lookup_key, artist_name in sample_lookup_keys_from_cache(limit=limit)
    ]


def main() -> None:
    """Run local and optional live API checks for artist image readiness."""
    args = _parse_args()
    _configure_logging(args.verbose)

    if args.lookup_key:
        lookup_key = args.lookup_key
        artist_name = args.artist_name or lookup_key
        targets = [(lookup_key, artist_name, lookup_key)]
    elif args.from_api:
        targets = _targets_from_running_api(args.base_url, args.limit, args.timeout)
        if not targets:
            LOGGER.warning(
                "API returned no recommendation artists; falling back to cache samples",
            )
            targets = _targets_from_cache_samples(args.limit)
    else:
        targets = _targets_from_cache_samples(args.limit)

    if not targets:
        raise SystemExit("No artist targets found to verify.")

    report = verify_artist_image_pipeline(targets)
    for check in report.checks:
        LOGGER.info(
            "%s %s (%s): %s",
            check.status,
            check.lookup_key,
            check.artist_name,
            check.detail,
        )

    if args.from_api:
        _verify_batch_endpoint(args.base_url, targets, timeout=args.timeout)

    if report.ready_count < len(report.checks):
        ready = report.ready_count
        total = len(report.checks)
        raise SystemExit(f"Artist image pipeline incomplete: {ready}/{total} ready")

    LOGGER.info(
        "Artist image pipeline verified for %s artist(s)",
        report.ready_count,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running API server.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of artists to verify.",
    )
    parser.add_argument(
        "--lookup-key",
        default=None,
        help="Verify one explicit lookup key instead of sampling.",
    )
    parser.add_argument(
        "--artist-name",
        default="",
        help="Artist display name for --lookup-key checks.",
    )
    parser.add_argument(
        "--from-api",
        action="store_true",
        help="Sample artists from archive and new-review recommendation endpoints.",
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
    """Configure console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def _targets_from_running_api(
    base_url: str,
    limit: int,
    timeout: float,
) -> list[tuple[str, str, str]]:
    """Collect artist targets from live recommendation endpoints."""
    community_id = _first_local_community_id()
    if community_id is None:
        return []
    profile = _profile_payload(community_id)
    targets: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        archive_body = {"profile": profile, "limit": limit, "offset": 0}
        new_reviews_body = {
            "profile": profile,
            "newest_count": 20,
            "limit": limit,
            "offset": 0,
        }
        for path, body in (
            ("/v1/recommendations/archive", archive_body),
            ("/v1/recommendations/new-reviews", new_reviews_body),
        ):
            response = client.post(path, json=body)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items")
            if not isinstance(items, list):
                continue
            artist_targets = artist_targets_from_recommendation_items(
                items,
                limit=limit,
            )
            for lookup_key, artist_name, artist_mbid in artist_targets:
                if lookup_key in seen:
                    continue
                seen.add(lookup_key)
                targets.append((lookup_key, artist_name, artist_mbid))
                if len(targets) >= limit:
                    return targets
    return targets


def _verify_batch_endpoint(
    base_url: str,
    targets: list[tuple[str, str, str]],
    *,
    timeout: float,
) -> None:
    """POST /v1/artists/images and verify each ready target returns an image."""
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        response = client.post(
            "/v1/artists/images",
            json={
                "artists": [
                    {"artist_mbid": artist_mbid, "artist_name": artist_name}
                    for _, artist_name, artist_mbid in targets
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items")
        if not isinstance(items, list):
            msg = f"Unexpected batch response: {payload!r}"
            raise RuntimeError(msg)

        for item in items:
            if not isinstance(item, dict):
                continue
            lookup_key = str(item.get("artist_mbid", ""))
            local = check_artist_image_api_readiness(
                lookup_key,
                artist_name=lookup_key,
            )
            if local.status != "ready":
                continue
            image = item.get("image")
            if not isinstance(image, dict):
                msg = f"Batch API returned null image for ready cache key {lookup_key}"
                raise RuntimeError(msg)
            file_path = str(image.get("thumbnail_url", ""))
            file_response = client.get(file_path)
            if file_response.status_code != 200:
                status_code = file_response.status_code
                msg = f"Image file endpoint failed for {lookup_key}: {status_code}"
                raise RuntimeError(msg)
            LOGGER.info("Batch API ok for %s", lookup_key)


def _first_local_community_id() -> str | None:
    """Return the first known local resolution-10 community id."""
    for community in load_communities_res_10():
        community_id = community.get("id")
        if community_id:
            return str(community_id)
    return None


def _profile_payload(community_id: str) -> dict[str, Any]:
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


if __name__ == "__main__":
    main()
