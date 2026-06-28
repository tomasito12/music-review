"""Confidence scoring for Wikimedia Commons artist image candidates."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from os import getenv
from typing import Any, Literal

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.pipeline.enrichment.commons_artist_match import (
    artist_name_in_text,
    commons_image_matches_artist,
    normalize_artist_match_text,
)

ResolutionSource = Literal[
    "wikidata_p18",
    "wikipedia",
    "commons_search",
    "member_fallback",
]

CURRENT_VALIDATION_VERSION = 1

DEFAULT_MIN_CONFIDENCE_MBID = 70
DEFAULT_MIN_CONFIDENCE_NAME = 85
DEFAULT_MIN_CONFIDENCE_MEMBER = 90

_HARD_REJECT_SCORE = -10_000

_EXCLUDED_CONTENT_RE = re.compile(
    r"\b(?:map|flag|logo|icon|diagram|locator|province|region|coat of arms|seal|"
    r"stadium|venue|aquarium|theme park|seaworld|zoo|airport|university|"
    r"album cover|single cover|screenshot|music video|official video|"
    r"discography|signature|war memorial|geography|geographic|administrative|"
    r"territory|municipality|county|district|national park)\b",
    flags=re.IGNORECASE,
)

_GEO_CATEGORY_RE = re.compile(
    r"\b(?:maps of|locator maps|geography of|regions of|provinces of|"
    r"administrative divisions|coat of arms of)\b",
    flags=re.IGNORECASE,
)

_MUSIC_CONTEXT_RE = re.compile(
    r"\b(?:band|musician|singer|rapper|musical group|dj|orchestra|ensemble|"
    r"concert|festival|performance|on stage|onstage|tour|live music|"
    r"rock band|indie band|pop band|punk band)\b",
    flags=re.IGNORECASE,
)

_VENUE_CONTEXT_RE = re.compile(
    r"\b(?:seaworld|theme park|amusement park|aquarium|zoo|stadium|arena|"
    r"before the show|opening ceremony|pre-show|preshow|venue|theatre|"
    r"theater|television show|tv show|geographical feature|province of|"
    r"region of|map of)\b",
    flags=re.IGNORECASE,
)

_PREFERRED_FILENAME_RE = re.compile(
    r"(live|concert|perform|press|portrait|band|festival|on.?stage|tour)",
    flags=re.IGNORECASE,
)


@dataclass(slots=True, frozen=True)
class ArtistContext:
    """Optional metadata hints used during image confidence scoring."""

    artist_mbid: str | None = None
    artist_type: str | None = None
    artist_country: str | None = None
    artist_disambiguation: str | None = None
    artist_tags: tuple[str, ...] = ()
    main_genres: tuple[str, ...] = ()
    artist_members: tuple[str, ...] = ()
    resolution_source: ResolutionSource = "commons_search"
    depicts_member_name: str | None = None


@dataclass(slots=True)
class CommonsImageConfidence:
    """Result of scoring one Commons image candidate."""

    score: int
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    threshold: int = 0


def min_confidence_mbid() -> int:
    """Return the minimum confidence score for MBID-backed lookups."""
    return _parse_int_env(
        "ARTIST_IMAGE_MIN_CONFIDENCE_MBID",
        DEFAULT_MIN_CONFIDENCE_MBID,
    )


def min_confidence_name() -> int:
    """Return the minimum confidence score for name-only lookups."""
    return _parse_int_env(
        "ARTIST_IMAGE_MIN_CONFIDENCE_NAME",
        DEFAULT_MIN_CONFIDENCE_NAME,
    )


def min_confidence_member() -> int:
    """Return the minimum confidence score for member-photo fallback."""
    return _parse_int_env(
        "ARTIST_IMAGE_MIN_CONFIDENCE_MEMBER",
        DEFAULT_MIN_CONFIDENCE_MEMBER,
    )


def confidence_threshold_for_context(context: ArtistContext | None) -> int:
    """Return the acceptance threshold for one artist context."""
    if context is None:
        return min_confidence_name()
    if context.resolution_source == "member_fallback":
        return min_confidence_member()
    if context.artist_mbid:
        return min_confidence_mbid()
    return min_confidence_name()


def score_commons_image_candidate(
    artist_name: str,
    commons_title: str,
    imageinfo: dict[str, Any] | None,
    *,
    context: ArtistContext | None = None,
) -> CommonsImageConfidence:
    """Score one Commons file and decide whether it is safe to cache."""
    name = artist_name.strip()
    if not name:
        return CommonsImageConfidence(
            score=_HARD_REJECT_SCORE,
            accepted=False,
            reasons=["empty_artist_name"],
        )

    lookup_name = (
        context.depicts_member_name.strip()
        if context is not None and context.depicts_member_name
        else name
    )
    threshold = confidence_threshold_for_context(context)
    reasons: list[str] = []
    score = 0

    context_text = _build_context_text(commons_title, imageinfo)
    normalized_file = normalize_artist_match_text(_filename_from_title(commons_title))

    if _EXCLUDED_CONTENT_RE.search(context_text):
        return CommonsImageConfidence(
            score=_HARD_REJECT_SCORE,
            accepted=False,
            reasons=["excluded_content_type"],
            threshold=threshold,
        )

    if not _artist_matches_commons_candidate(lookup_name, commons_title, imageinfo):
        return CommonsImageConfidence(
            score=_HARD_REJECT_SCORE,
            accepted=False,
            reasons=["artist_name_mismatch"],
            threshold=threshold,
        )
    reasons.append("artist_name_match")
    score += 40

    categories = _metadata_value(imageinfo, "Categories") or ""
    if categories and _GEO_CATEGORY_RE.search(categories):
        if not _MUSIC_CONTEXT_RE.search(context_text):
            return CommonsImageConfidence(
                score=_HARD_REJECT_SCORE,
                accepted=False,
                reasons=["geography_category_without_music_context"],
                threshold=threshold,
            )
        reasons.append("geography_with_music_context")
        score -= 15

    if _VENUE_CONTEXT_RE.search(context_text):
        if not _MUSIC_CONTEXT_RE.search(context_text):
            return CommonsImageConfidence(
                score=_HARD_REJECT_SCORE,
                accepted=False,
                reasons=["venue_or_non_music_context"],
                threshold=threshold,
            )
        reasons.append("venue_with_music_context")
        score -= 20

    if _MUSIC_CONTEXT_RE.search(context_text):
        score += 25
        reasons.append("music_context")

    if _PREFERRED_FILENAME_RE.search(normalized_file):
        score += 10
        reasons.append("preferred_filename")

    if context is not None:
        score += _score_artist_context(context, context_text, reasons)
        if context.artist_mbid and context.resolution_source == "wikidata_p18":
            score += 15
            reasons.append("wikidata_resolution_path")
        elif context.artist_mbid:
            score += 10
            reasons.append("mbid_backed_lookup")

    accepted = score >= threshold
    if not accepted:
        reasons.append("below_threshold")
    return CommonsImageConfidence(
        score=score,
        accepted=accepted,
        reasons=reasons,
        threshold=threshold,
    )


def score_parsed_commons_image(
    artist_name: str,
    info: CommonsImageInfo,
    *,
    context: ArtistContext | None = None,
    imageinfo: dict[str, Any] | None = None,
) -> CommonsImageConfidence:
    """Score one parsed CommonsImageInfo record."""
    title = f"File:{info.commons_file.replace(' ', '_')}"
    payload = imageinfo if imageinfo is not None else _imageinfo_from_parsed(info)
    return score_commons_image_candidate(
        artist_name,
        title,
        payload,
        context=context,
    )


def member_name_eligible_for_fallback(member_name: str) -> bool:
    """Return whether a band member name is distinctive enough for fallback."""
    normalized = normalize_artist_match_text(member_name)
    if not normalized:
        return False
    tokens = normalized.split()
    return not (len(tokens) == 1 and len(tokens[0]) <= 4)


def _score_artist_context(
    context: ArtistContext,
    context_text: str,
    reasons: list[str],
) -> int:
    """Add context-based score adjustments."""
    score = 0
    if context.artist_mbid and context.resolution_source == "wikidata_p18":
        score += 20
        reasons.append("mbid_wikidata_link")

    disambiguation = (context.artist_disambiguation or "").strip()
    if disambiguation and artist_name_in_text(disambiguation, context_text):
        score += 15
        reasons.append("disambiguation_in_metadata")

    if context.artist_type and context.artist_type.casefold() in {
        "group",
        "person",
        "orchestra",
    }:
        score += 5
        reasons.append("known_artist_type")

    if context.resolution_source == "member_fallback":
        score -= 10
        reasons.append("member_fallback_penalty")

    return score


def _artist_matches_commons_candidate(
    artist_name: str,
    commons_title: str,
    imageinfo: dict[str, Any] | None,
) -> bool:
    """Return whether an artist name matches one Commons candidate."""
    if commons_image_matches_artist(artist_name, commons_title, imageinfo):
        return True

    object_name = _metadata_value(imageinfo, "ObjectName")
    filename = _filename_from_title(commons_title)
    for part in (object_name, filename):
        if not part:
            continue
        if artist_name_in_text(artist_name, part) or artist_name_in_text(
            part,
            artist_name,
        ):
            return True
    return False


def _build_context_text(
    commons_title: str,
    imageinfo: dict[str, Any] | None,
) -> str:
    """Combine filename and Commons metadata into searchable text."""
    parts = [_filename_from_title(commons_title)]
    if imageinfo is None:
        return " ".join(parts)

    metadata = imageinfo.get("extmetadata")
    if not isinstance(metadata, dict):
        return " ".join(parts)

    for key in ("ObjectName", "ImageDescription", "Artist", "Credit", "Categories"):
        value = _metadata_value(imageinfo, key)
        if value is not None:
            parts.append(value)
    return " ".join(parts)


def _imageinfo_from_parsed(info: CommonsImageInfo) -> dict[str, Any]:
    """Build a minimal imageinfo dict from parsed Commons metadata."""
    extmetadata: dict[str, dict[str, str]] = {
        "ObjectName": {"value": info.title or info.commons_file},
        "LicenseShortName": {"value": info.license},
    }
    if info.attribution_text:
        extmetadata["ImageDescription"] = {"value": info.attribution_text}
    if info.author:
        extmetadata["Artist"] = {"value": info.author}
    return {"extmetadata": extmetadata}


def _filename_from_title(commons_title: str) -> str:
    """Return the bare filename from a Commons title."""
    if commons_title.lower().startswith("file:"):
        return commons_title[5:].replace("_", " ")
    return commons_title.replace("_", " ")


def _metadata_value(
    imageinfo: dict[str, Any] | None,
    key: str,
) -> str | None:
    """Read one extmetadata string value."""
    if imageinfo is None:
        return None
    metadata = imageinfo.get("extmetadata")
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get(key)
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if value is None:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", str(value))).strip()
    return text or None


def _parse_int_env(name: str, default: int) -> int:
    """Parse a positive integer from the environment."""
    raw = getenv(name, str(default))
    try:
        parsed = int(raw)
    except ValueError:
        return default
    return max(0, parsed)
