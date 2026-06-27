"""Data models for cached artist images from Wikimedia Commons."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

ArtistImageStatus = Literal["ok", "not_found"]


@dataclass(slots=True)
class ArtistImageRecord:
    """One cached artist image lookup result."""

    artist_mbid: str
    artist_name: str
    status: ArtistImageStatus
    fetched_at: str
    wikidata_id: str | None = None
    commons_file: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    license: str | None = None
    license_url: str | None = None
    author: str | None = None
    source_url: str | None = None
    attribution_text: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict for JSONL storage."""
        payload: dict[str, Any] = {
            "artist_mbid": self.artist_mbid,
            "artist_name": self.artist_name,
            "status": self.status,
            "fetched_at": self.fetched_at,
        }
        optional_fields = (
            "wikidata_id",
            "commons_file",
            "image_url",
            "thumbnail_url",
            "license",
            "license_url",
            "author",
            "source_url",
            "attribution_text",
            "reason",
        )
        for key in optional_fields:
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ArtistImageRecord:
        """Build a record from one JSONL object."""
        status_raw = payload.get("status")
        parsed_status: ArtistImageStatus = "ok" if status_raw == "ok" else "not_found"
        return cls(
            artist_mbid=str(payload.get("artist_mbid", "")),
            artist_name=str(payload.get("artist_name", "")),
            status=parsed_status,
            fetched_at=str(payload.get("fetched_at", "")),
            wikidata_id=_optional_str(payload.get("wikidata_id")),
            commons_file=_optional_str(payload.get("commons_file")),
            image_url=_optional_str(payload.get("image_url")),
            thumbnail_url=_optional_str(payload.get("thumbnail_url")),
            license=_optional_str(payload.get("license")),
            license_url=_optional_str(payload.get("license_url")),
            author=_optional_str(payload.get("author")),
            source_url=_optional_str(payload.get("source_url")),
            attribution_text=_optional_str(payload.get("attribution_text")),
            reason=_optional_str(payload.get("reason")),
        )


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _optional_str(value: object) -> str | None:
    """Return a stripped string or None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class CommonsImageInfo:
    """Parsed Wikimedia Commons file metadata."""

    commons_file: str
    image_url: str
    thumbnail_url: str
    license: str
    license_url: str | None
    author: str
    source_url: str
    attribution_text: str
    title: str = field(default="")
