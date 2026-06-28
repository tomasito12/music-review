"""Tests for artist image batch and pipeline helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from music_review.application.artist_image_batch import (
    ArtistImageBatchReport,
    ArtistImageTarget,
    artist_lookup_from_review_metadata,
    artist_targets_from_metadata,
    batch_selection_slice,
    fetch_missing_artist_images,
    run_artist_image_batch,
    split_targets_by_queue,
    write_batch_report,
)
from music_review.application.artist_image_models import ArtistImageRecord, utc_now_iso


def test_unique_artists_from_metadata_deduplicates_mbids(tmp_path: Path) -> None:
    """Metadata sampling returns one row per artist MBID."""
    from music_review.application.artist_image_batch import unique_artists_from_metadata

    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        "\n".join(
            [
                '{"review_id": 1, "artist": "Alpha", "artist_mbid": "mbid-1"}',
                '{"review_id": 2, "artist": "Alpha Dup", "artist_mbid": "mbid-1"}',
                '{"review_id": 3, "artist": "Beta", "artist_mbid": "mbid-2"}',
            ],
        ),
        encoding="utf-8",
    )

    assert unique_artists_from_metadata(metadata_path) == [
        ("mbid-1", "Alpha"),
        ("mbid-2", "Beta"),
    ]


def test_artist_targets_from_metadata_includes_name_only_queue(
    tmp_path: Path,
) -> None:
    """Metadata aggregation emits MBID and name-only artist targets."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        "\n".join(
            [
                (
                    '{"review_id": 1, "artist": "Alpha", "artist_mbid": "mbid-1", '
                    '"artist_type": "Group", "artist_members": ["Member One"]}'
                ),
                '{"review_id": 2, "artist": "No Mbid Artist"}',
            ],
        ),
        encoding="utf-8",
    )

    targets = artist_targets_from_metadata(metadata_path)
    by_key = {target.lookup_key: target for target in targets}

    assert by_key["mbid-1"].artist_type == "Group"
    assert by_key["mbid-1"].artist_members == ("Member One",)
    assert by_key["name:no mbid artist"].artist_mbid is None


def test_batch_selection_slice_process_all_ignores_limit() -> None:
    """The --all flag selects every target after the offset."""
    targets = [
        ArtistImageTarget(
            lookup_key=f"mbid-{index}",
            artist_name=f"Artist {index}",
            artist_mbid=f"mbid-{index}",
            artist_type=None,
            artist_country=None,
            artist_disambiguation=None,
            artist_members=(),
            main_genres=(),
            review_count=1,
        )
        for index in range(5)
    ]

    assert len(batch_selection_slice(targets, offset=0, limit=1, process_all=True)) == 5
    assert len(batch_selection_slice(targets, offset=2, limit=1, process_all=True)) == 3
    limited = batch_selection_slice(targets, offset=0, limit=2, process_all=False)
    assert len(limited) == 2


def test_split_targets_by_queue_filters_name_only_artists() -> None:
    """Queue selection limits batch slices to MBID or name-only artists."""
    targets = [
        ArtistImageTarget(
            lookup_key="mbid-1",
            artist_name="Alpha",
            artist_mbid="mbid-1",
            artist_type=None,
            artist_country=None,
            artist_disambiguation=None,
            artist_members=(),
            main_genres=(),
            review_count=2,
        ),
        ArtistImageTarget(
            lookup_key="name:beta",
            artist_name="Beta",
            artist_mbid=None,
            artist_type=None,
            artist_country=None,
            artist_disambiguation=None,
            artist_members=(),
            main_genres=(),
            review_count=1,
        ),
    ]

    assert len(split_targets_by_queue(targets, queue="mbid")) == 1
    assert len(split_targets_by_queue(targets, queue="name")) == 1


def test_run_artist_image_batch_revalidate_downgrades_bad_cache(
    tmp_path: Path,
) -> None:
    """Revalidation downgrades cached ok entries that fail current rules."""
    from music_review.application.artist_image_service import ArtistImageService
    from music_review.application.artist_image_store import upsert_artist_image

    cache_path = tmp_path / "artist_images.jsonl"
    upsert_artist_image(
        cache_path,
        ArtistImageRecord(
            artist_mbid="mbid-map",
            artist_name="Ortego",
            status="ok",
            fetched_at=utc_now_iso(),
            commons_file="Ortego map.svg",
            attribution_text="Locator map of Otago province",
            source_url="https://commons.wikimedia.org/wiki/File:Ortego_map.svg",
        ),
    )

    class RevalidateService:
        """Service stub that revalidates against the real cache file."""

        cache_path: Path

        def cached_record(self, artist_mbid: str) -> ArtistImageRecord | None:
            from music_review.application.artist_image_store import (
                load_artist_image_index,
            )

            return load_artist_image_index(self.cache_path).get(artist_mbid)

        def revalidate_record(self, record, *, context=None):
            real = ArtistImageService(
                cache_path=self.cache_path,
                images_dir=tmp_path / "artist_images",
            )
            return real.revalidate_record(record, context=context)

    service = RevalidateService()
    service.cache_path = cache_path
    target = ArtistImageTarget(
        lookup_key="mbid-map",
        artist_name="Ortego",
        artist_mbid="mbid-map",
        artist_type=None,
        artist_country=None,
        artist_disambiguation=None,
        artist_members=(),
        main_genres=(),
        review_count=1,
    )
    report = run_artist_image_batch(
        service,
        [target],
        limit=1,
        revalidate=True,
    )

    assert report.revalidated_downgraded == 1


def test_write_batch_report_writes_json(tmp_path: Path) -> None:
    """Batch reports are persisted as JSON summaries."""
    report_path = tmp_path / "report.json"
    write_batch_report(ArtistImageBatchReport(attempted=3, resolved_ok=1), report_path)
    assert '"attempted": 3' in report_path.read_text(encoding="utf-8")


def test_artist_lookup_from_review_metadata_returns_mbid_and_name() -> None:
    """Review metadata lookup exposes artist MBID and display name."""
    metadata = {
        10: {"artist": "Radiohead", "artist_mbid": "mbid-rh"},
        11: {"artist": "Unknown"},
    }

    assert artist_lookup_from_review_metadata(metadata, 10) == ("mbid-rh", "Radiohead")
    assert artist_lookup_from_review_metadata(metadata, 11) == (None, "Unknown")
    assert artist_lookup_from_review_metadata(metadata, 99) == (None, "")


@dataclass
class FakeArtistImageLookupService:
    """Stub service for batch fetch tests."""

    cached_mbids: set[str] = field(default_factory=set)
    lookup_calls: list[str] = field(default_factory=list)

    def cached_record(self, artist_mbid: str) -> ArtistImageRecord | None:
        """Return a cached ok record for selected MBIDs."""
        if artist_mbid not in self.cached_mbids:
            return None
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_mbid,
            status="ok",
            fetched_at=utc_now_iso(),
        )

    def is_negative_cache_fresh(self, record: ArtistImageRecord) -> bool:
        """Negative cache is never fresh in this stub."""
        return record.status == "not_found"

    def lookup(
        self,
        artist_mbid: str,
        *,
        artist_name: str | None = None,
    ) -> ArtistImageRecord:
        """Record one lookup and return an ok record."""
        self.lookup_calls.append(artist_mbid)
        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_name or artist_mbid,
            status="ok",
            fetched_at=utc_now_iso(),
            thumbnail_url="https://example.com/thumb.jpg",
        )


def test_fetch_missing_artist_images_respects_limit() -> None:
    """Batch fetch only resolves artists that are not already cached."""
    service = FakeArtistImageLookupService(cached_mbids={"mbid-cached"})

    resolved = fetch_missing_artist_images(
        service,
        [("mbid-cached", "Cached"), ("mbid-new", "New"), ("mbid-later", "Later")],
        limit=1,
    )

    assert resolved == 1
    assert service.lookup_calls == ["mbid-new"]
