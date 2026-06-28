"""Tests for artist image pipeline verification helpers."""

from __future__ import annotations

from pathlib import Path

from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso
from music_review.application.artist_image_pipeline_verify import (
    artist_targets_from_recommendation_items,
    check_artist_image_api_readiness,
    check_local_artist_image_cache,
    verify_artist_image_pipeline,
)
from music_review.application.artist_image_service import ArtistImageService
from music_review.application.artist_image_store import upsert_artist_image


def _ok_record(lookup_key: str, *, artist_name: str = "Alpha") -> ArtistImageRecord:
    return ArtistImageRecord(
        artist_mbid=lookup_key,
        artist_name=artist_name,
        status="ok",
        fetched_at=utc_now_iso(),
        thumbnail_url="https://example.com/alpha.jpg",
        license="CC BY 4.0",
        attribution_text="Alpha by User",
        source_url="https://commons.wikimedia.org/wiki/File:Alpha.jpg",
        local_path=f"artist_images/{lookup_key}.jpg",
    )


def test_check_local_artist_image_cache_reports_missing_jsonl(tmp_path: Path) -> None:
    check = check_local_artist_image_cache(
        "mbid-missing",
        artist_name="Missing",
        cache_path=tmp_path / "artist_images.jsonl",
        images_dir=tmp_path / "artist_images",
    )

    assert check.status == "missing_jsonl"


def test_check_local_artist_image_cache_reports_missing_jpg(tmp_path: Path) -> None:
    cache_path = tmp_path / "artist_images.jsonl"
    images_dir = tmp_path / "artist_images"
    upsert_artist_image(cache_path, _ok_record("mbid-alpha"))

    check = check_local_artist_image_cache(
        "mbid-alpha",
        artist_name="Alpha",
        cache_path=cache_path,
        images_dir=images_dir,
    )

    assert check.status == "missing_jpg"


def test_check_artist_image_api_readiness_reports_ready_with_jsonl_and_jpg(
    tmp_path: Path,
) -> None:
    cache_path = tmp_path / "artist_images.jsonl"
    images_dir = tmp_path / "artist_images"
    images_dir.mkdir()
    upsert_artist_image(cache_path, _ok_record("mbid-alpha"))
    (images_dir / "mbid-alpha.jpg").write_bytes(b"fake-jpeg")
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=images_dir,
        resolve_on_demand=False,
    )

    check = check_artist_image_api_readiness(
        "mbid-alpha",
        artist_name="Alpha",
        artist_mbid="mbid-alpha",
        service=service,
    )

    assert check.status == "ready"
    assert "/v1/artists/mbid-alpha/image/file" in check.detail


def test_artist_targets_from_recommendation_items_deduplicates_artists() -> None:
    items = [
        {"artist": "Alpha", "artist_mbid": "mbid-1"},
        {"artist": "Alpha", "artist_mbid": "mbid-1"},
        {"artist": "Beta", "artist_mbid": None},
    ]

    targets = artist_targets_from_recommendation_items(items, limit=5)

    assert targets == [
        ("mbid-1", "Alpha", "mbid-1"),
        ("name:beta", "Beta", ""),
    ]


def test_verify_artist_image_pipeline_summarizes_checks(tmp_path: Path) -> None:
    cache_path = tmp_path / "artist_images.jsonl"
    images_dir = tmp_path / "artist_images"
    images_dir.mkdir()
    upsert_artist_image(cache_path, _ok_record("mbid-alpha"))
    (images_dir / "mbid-alpha.jpg").write_bytes(b"fake-jpeg")
    service = ArtistImageService(
        cache_path=cache_path,
        images_dir=images_dir,
        resolve_on_demand=False,
    )

    report = verify_artist_image_pipeline(
        [
            ("mbid-alpha", "Alpha", "mbid-alpha"),
            ("mbid-missing", "Missing", "mbid-missing"),
        ],
        service=service,
    )

    assert report.ready_count == 1
    assert report.checks[0].status == "ready"
    assert report.checks[1].status == "missing_jsonl"
