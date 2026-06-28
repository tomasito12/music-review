"""Tests for artist image batch CLI."""

from __future__ import annotations

from pathlib import Path

from music_review.application.artist_image_batch import ArtistImageBatchReport
from music_review.pipeline.enrichment import artist_image_batch_cli as cli


def test_batch_cli_runs_with_no_targets(tmp_path: Path, monkeypatch) -> None:
    """CLI exits cleanly when metadata contains no artist rows."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "resolve_data_path", lambda path: path)

    assert cli.main(["--metadata", str(metadata_path), "--limit", "1"]) == 0


def test_batch_cli_writes_report(tmp_path: Path, monkeypatch) -> None:
    """CLI can persist a JSON batch report."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        '{"review_id": 1, "artist": "Alpha", "artist_mbid": "mbid-1"}\n',
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(cli, "resolve_data_path", lambda path: path)
    monkeypatch.setattr(
        cli,
        "default_artist_image_service",
        lambda: _NoResolveService(),
    )

    assert (
        cli.main(
            [
                "--metadata",
                str(metadata_path),
                "--limit",
                "1",
                "--force",
                "--report",
                str(report_path),
            ],
        )
        == 0
    )
    assert report_path.is_file()


def test_batch_cli_process_all_flag(tmp_path: Path, monkeypatch) -> None:
    """CLI --all forwards process_all to the batch runner."""
    metadata_path = tmp_path / "metadata.jsonl"
    metadata_path.write_text(
        "\n".join(
            (
                f'{{"review_id": {index}, "artist": "Artist {index}", '
                f'"artist_mbid": "mbid-{index}"}}'
            )
            for index in range(5)
        ),
        encoding="utf-8",
    )
    captured: dict[str, bool] = {}

    def fake_run(_service, _targets, **kwargs):
        captured["process_all"] = kwargs["process_all"]
        return ArtistImageBatchReport(attempted=5)

    monkeypatch.setattr(cli, "resolve_data_path", lambda path: path)
    monkeypatch.setattr(
        cli,
        "default_artist_image_service",
        lambda: _NoResolveService(),
    )
    monkeypatch.setattr(cli, "run_artist_image_batch", fake_run)

    assert cli.main(["--metadata", str(metadata_path), "--all", "--force"]) == 0
    assert captured["process_all"] is True


class _NoResolveService:
    """Stub service that records one synthetic not_found lookup."""

    download_enabled = False

    def lookup(self, artist_mbid, *, artist_name=None, force=False, context=None):
        from music_review.application.artist_image_models import (
            ArtistImageRecord,
            utc_now_iso,
        )

        return ArtistImageRecord(
            artist_mbid=artist_mbid,
            artist_name=artist_name or artist_mbid,
            status="not_found",
            fetched_at=utc_now_iso(),
            reason="test_stub",
        )

    def cached_record(self, _lookup_key):
        return None

    def is_negative_cache_fresh(self, _record):
        return False

    def revalidate_record(self, record, *, context=None):
        return record
