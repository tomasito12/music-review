"""Download artist thumbnails to local cache files."""

from __future__ import annotations

import logging
from os import getenv
from pathlib import Path

import requests

from music_review.pipeline.enrichment.wikimedia_http import WIKIMEDIA_HEADERS

logger = logging.getLogger(__name__)

LOCAL_IMAGE_SUBDIR = "artist_images"
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 30


def artist_image_download_enabled() -> bool:
    """Return whether resolved thumbnails should be stored under data/."""
    return getenv("ARTIST_IMAGE_DOWNLOAD", "false").lower() == "true"


def local_image_relative_path(artist_mbid: str) -> str:
    """Return the relative data path for one cached artist image file."""
    return f"{LOCAL_IMAGE_SUBDIR}/{artist_mbid.strip()}.jpg"


def local_image_file_path(images_dir: Path, artist_mbid: str) -> Path:
    """Return the absolute path for one cached artist image file."""
    return images_dir / f"{artist_mbid.strip()}.jpg"


def download_thumbnail(thumbnail_url: str, dest_path: Path) -> bool:
    """Download one thumbnail URL to a local JPG file."""
    url = thumbnail_url.strip()
    if not url:
        return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(
            url,
            headers=WIKIMEDIA_HEADERS,
            timeout=DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning(
            "Failed to download artist thumbnail from %s (HTTP %s)",
            url,
            status,
        )
        return False
    except requests.RequestException:
        logger.warning("Failed to download artist thumbnail from %s", url)
        return False

    content_type = response.headers.get("Content-Type", "")
    if content_type and not content_type.startswith("image/"):
        logger.warning("Thumbnail URL did not return an image: %s", url)
        return False

    dest_path.write_bytes(response.content)
    logger.info("Stored local artist thumbnail at %s", dest_path)
    return True
