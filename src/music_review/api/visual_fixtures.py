"""Deterministic API fixtures for Playwright visual regression tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from PIL import Image

from music_review.api.app import create_app
from music_review.api.dependencies import get_artist_image_service, get_corpus_provider
from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.application.artist_image_service import ArtistImageService
from music_review.application.artist_image_store import upsert_artist_image
from music_review.domain.models import Review, Track

VISUAL_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "visual_fixtures"
VISUAL_IMAGE_MBIDS = (
    "mbid-radiohead",
    "mbid-arcade-fire",
    "mbid-national",
    "mbid-phoebe-bridgers",
    "mbid-notwist",
    "mbid-big-thief",
)

_VISUAL_EXCERPT = (
    "Ein Fundstück mit genug Ecken, Wärme und Nachhall, um nicht nach zwei Wochen "
    "wieder aus dem Kopf zu verschwinden. Die Platte trägt Spannung und Melodie "
    "gleichermaßen und bleibt dabei überraschend nahbar."
)

_VISUAL_COMMUNITIES: tuple[dict[str, Any], ...] = (
    {
        "id": "C001",
        "centroid": "Indie Rock",
        "top_artists": ["The Notwist", "Big Thief", "Wednesday"],
    },
    {
        "id": "C002",
        "centroid": "Elektronik",
        "top_artists": ["The Notwist", "Low"],
    },
    {
        "id": "C003",
        "centroid": "Indie Pop",
        "top_artists": ["Japanese Breakfast", "Wolf Alice"],
    },
    {
        "id": "C004",
        "centroid": "Melancholisch",
        "top_artists": ["Low", "Big Thief"],
    },
)

_VISUAL_REVIEW_SPECS: tuple[tuple[int, str, str, int, float, str | None], ...] = (
    (1, "Radiohead", "OK Computer", 1997, 10, "mbid-radiohead"),
    (2, "Arcade Fire", "Funeral", 2004, 9, "mbid-arcade-fire"),
    (3, "The National", "Boxer", 2007, 9, "mbid-national"),
    (4, "Bon Iver", "For Emma, Forever Ago", 2008, 8, None),
    (5, "Fleet Foxes", "Fleet Foxes", 2008, 8, None),
    (6, "Beach House", "Teen Dream", 2010, 8, None),
    (7, "Vampire Weekend", "Modern Vampires of the City", 2013, 8, None),
    (8, "St. Vincent", "Masseduction", 2017, 8, None),
    (9, "Phoebe Bridgers", "Punisher", 2020, 9, "mbid-phoebe-bridgers"),
    (10, "Fontaines D.C.", "Dogrel", 2019, 8, None),
    (11, "Black Country, New Road", "Ants From Up There", 2022, 9, None),
    (12, "Dry Cleaning", "New Long Leg", 2021, 8, None),
    (901, "The Notwist", "Vertigo Days", 2021, 8, "mbid-notwist"),
    (
        902,
        "Big Thief",
        "Dragon New Warm Mountain I Believe In You",
        2022,
        8,
        "mbid-big-thief",
    ),
    (903, "Japanese Breakfast", "Jubilee", 2021, 7, None),
    (904, "Dry Cleaning", "New Long Leg", 2021, 8, None),
    (905, "Low", "HEY WHAT", 2021, 9, None),
    (906, "Wednesday", "Rat Saw God", 2023, 8, None),
    (907, "Fontaines D.C.", "Skinty Fia", 2022, 8, None),
    (908, "Wolf Alice", "Blue Weekend", 2021, 8, None),
)

_COMMUNITY_ROTATION = ("C001", "C002", "C003", "C004")


@dataclass(frozen=True, slots=True)
class VisualCorpusProvider:
    """Small deterministic corpus for visual regression screenshots."""

    def reviews(self) -> Sequence[Review]:
        """Return the visual fixture review corpus."""
        return tuple(_build_review(spec) for spec in _VISUAL_REVIEW_SPECS)

    def newest_reviews(self, count: int) -> Sequence[Review]:
        """Return the newest visual fixture reviews by id."""
        newest = [review for review in self.reviews() if review.id >= 900]
        newest.sort(key=lambda review: review.id, reverse=True)
        return tuple(newest[: max(1, count)])

    def metadata(self) -> Mapping[int, Mapping[str, Any]]:
        """Return metadata with optional artist MBIDs."""
        metadata: dict[int, dict[str, Any]] = {}
        for spec in _VISUAL_REVIEW_SPECS:
            review_id = spec[0]
            artist_mbid = spec[5]
            row: dict[str, Any] = {"labels": ["Visual Fixture Label"]}
            if artist_mbid is not None:
                row["artist_mbid"] = artist_mbid
            metadata[review_id] = row
        return metadata

    def affinities(self) -> Sequence[Mapping[str, Any]]:
        """Return album-community affinities for all fixture reviews."""
        return tuple(
            _affinity_for_review(review_id) for review_id, *_ in _VISUAL_REVIEW_SPECS
        )

    def affinities_by_review_id(self) -> Mapping[int, Mapping[str, Any]]:
        """Return affinities keyed by review id."""
        return {int(row["review_id"]): row for row in self.affinities()}

    def memberships(self) -> dict[str, dict[str, str]]:
        """Return empty artist-community memberships."""
        return {}

    def communities(self) -> Sequence[Mapping[str, Any]]:
        """Return community metadata used by the visual profile."""
        return _VISUAL_COMMUNITIES

    def broad_categories(self) -> tuple[list[str], dict[str, list[str]]]:
        """Return broad categories for filter UI."""
        return (
            ["Rock & Alternative", "Electronic & Dance", "Pop & Indie"],
            {
                "C001": ["Rock & Alternative"],
                "C002": ["Electronic & Dance"],
                "C003": ["Pop & Indie"],
                "C004": ["Rock & Alternative"],
            },
        )

    def genre_labels(self) -> Mapping[str, str]:
        """Return readable community labels."""
        return {
            "C001": "Indie Rock",
            "C002": "Elektronik",
            "C003": "Indie Pop",
            "C004": "Melancholisch",
        }

    def plattenlabels(self) -> Sequence[str]:
        """Return fixture record labels."""
        return ["Visual Fixture Label"]

    def year_floor(self) -> int:
        """Return the lowest release year in the fixture corpus."""
        return 1997

    def year_cap(self) -> int:
        """Return the highest release year in the fixture corpus."""
        return 2023

    def artist_mbid_for_review(self, review_id: int) -> str | None:
        """Return the MusicBrainz artist ID for one fixture review."""
        for spec_review_id, *_rest, artist_mbid in _VISUAL_REVIEW_SPECS:
            if spec_review_id == review_id:
                return artist_mbid
        return None


def visual_fixtures_dir() -> Path:
    """Return the root directory for committed visual API fixtures."""
    return VISUAL_FIXTURES_DIR


def create_visual_artist_image_service() -> ArtistImageService:
    """Build an artist image service backed by local fixture JPG files."""
    fixtures_dir = visual_fixtures_dir()
    cache_path = fixtures_dir / "artist_images.jsonl"
    images_dir = fixtures_dir / "artist_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    _ensure_fixture_jpegs(images_dir)
    _ensure_fixture_cache(cache_path)
    return ArtistImageService(
        cache_path=cache_path,
        images_dir=images_dir,
        resolve_on_demand=False,
    )


def create_visual_app() -> FastAPI:
    """Return a FastAPI app wired to deterministic visual fixtures."""
    import music_review.application.newest_review_pool as newest_review_pool

    newest_review_pool.update_batches_path = lambda: (
        visual_fixtures_dir() / "update_batches.jsonl"
    )
    app = create_app()
    app.dependency_overrides[get_corpus_provider] = lambda: VisualCorpusProvider()
    app.dependency_overrides[get_artist_image_service] = (
        create_visual_artist_image_service
    )
    return app


def _build_review(
    spec: tuple[int, str, str, int, float, str | None],
) -> Review:
    review_id, artist, album, year, rating, _artist_mbid = spec
    return Review(
        id=review_id,
        url=f"https://www.plattentests.de/rezension/visual/{review_id}",
        artist=artist,
        album=album,
        text=f"{artist} - {album}. {_VISUAL_EXCERPT}",
        rating=rating,
        release_date=date(year, 6, 15),
        release_year=year,
        labels=["Visual Fixture Label"],
        tracklist=[
            Track(number=1, title="Opening", is_highlight=True),
            Track(number=2, title="Closing"),
        ],
    )


def _affinity_for_review(review_id: int) -> dict[str, object]:
    primary = _COMMUNITY_ROTATION[review_id % len(_COMMUNITY_ROTATION)]
    secondary = _COMMUNITY_ROTATION[(review_id + 1) % len(_COMMUNITY_ROTATION)]
    return {
        "review_id": review_id,
        "communities": {
            "res_10": [
                {"id": primary, "score": 0.88 - (review_id % 5) * 0.03},
                {"id": secondary, "score": 0.62 - (review_id % 3) * 0.04},
            ],
        },
    }


def _ensure_fixture_jpegs(images_dir: Path) -> None:
    colors = {
        "mbid-radiohead": (92, 108, 124),
        "mbid-arcade-fire": (148, 116, 92),
        "mbid-national": (118, 104, 88),
        "mbid-phoebe-bridgers": (176, 140, 128),
        "mbid-notwist": (196, 168, 138),
        "mbid-big-thief": (164, 132, 108),
    }
    for artist_mbid, rgb in colors.items():
        jpg_path = images_dir / f"{artist_mbid}.jpg"
        if jpg_path.is_file():
            continue
        image = Image.new("RGB", (640, 480), rgb)
        image.save(jpg_path, format="JPEG", quality=85)


def _ensure_fixture_cache(cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    records = {
        "mbid-radiohead": _ok_image_record("mbid-radiohead", "Radiohead"),
        "mbid-arcade-fire": _ok_image_record("mbid-arcade-fire", "Arcade Fire"),
        "mbid-national": _ok_image_record("mbid-national", "The National"),
        "mbid-phoebe-bridgers": _ok_image_record(
            "mbid-phoebe-bridgers",
            "Phoebe Bridgers",
        ),
        "mbid-notwist": _ok_image_record("mbid-notwist", "The Notwist"),
        "mbid-big-thief": _ok_image_record("mbid-big-thief", "Big Thief"),
    }
    for record in records.values():
        upsert_artist_image(cache_path, record)


def _ok_image_record(artist_mbid: str, artist_name: str) -> ArtistImageRecord:
    return ArtistImageRecord(
        artist_mbid=artist_mbid,
        artist_name=artist_name,
        status="ok",
        fetched_at=utc_now_iso(),
        thumbnail_url=f"https://example.com/{artist_mbid}.jpg",
        license="CC BY 4.0",
        attribution_text=f"{artist_name} (Visual Fixture), CC BY 4.0",
        source_url="https://commons.wikimedia.org/wiki/File:Visual-fixture.jpg",
        local_path=f"artist_images/{artist_mbid}.jpg",
    )
