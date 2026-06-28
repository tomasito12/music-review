"""License checks and attribution text for Commons artist images."""

from __future__ import annotations

import re

from music_review.application.artist_image_models import CommonsImageInfo

_REJECTED_LICENSE_FRAGMENTS = (
    "non-commercial",
    "noncommercial",
    "by-nc",
    "by-nd",
    "no derivatives",
    "noderivatives",
    "all rights reserved",
)


def normalize_license_name(license_name: str) -> str:
    """Normalize a license label for comparisons."""
    return re.sub(r"\s+", " ", license_name.strip().casefold())


def is_license_allowed(license_name: str) -> bool:
    """Return whether a Commons license is allowed for display."""
    normalized = normalize_license_name(license_name)
    if not normalized:
        return False
    if any(fragment in normalized for fragment in _REJECTED_LICENSE_FRAGMENTS):
        return False
    if "cc0" in normalized or "public domain" in normalized:
        return True
    if normalized.startswith("pd-"):
        return True
    return normalized.startswith("cc by") or normalized.startswith("cc-by")


def build_attribution_text(
    *,
    title: str,
    author: str,
    license_name: str,
    source_url: str,
) -> str:
    """Build a compact attribution line for UI display."""
    display_title = title.strip() or "Künstlerfoto"
    display_author = author.strip() or "unbekannt"
    display_license = license_name.strip() or "Lizenz unbekannt"
    return (
        f"„{display_title}“ von {display_author}, {display_license} "
        f"via Wikimedia Commons ({source_url})"
    )


def commons_image_to_record_fields(info: CommonsImageInfo) -> dict[str, str | None]:
    """Map parsed Commons metadata to artist-image record fields."""
    return {
        "commons_file": info.commons_file,
        "image_url": info.image_url,
        "thumbnail_url": info.thumbnail_url,
        "license": info.license,
        "license_url": info.license_url,
        "author": info.author,
        "source_url": info.source_url,
        "attribution_text": info.attribution_text,
    }
