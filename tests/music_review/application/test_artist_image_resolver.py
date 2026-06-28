"""Tests for artist image resolver orchestration."""

from __future__ import annotations

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.application.artist_image_resolver import resolve_artist_image


def _music_commons_info(
    *,
    commons_file: str,
    title: str,
    attribution: str | None = None,
) -> CommonsImageInfo:
    """Build a Commons image fixture with enough music context to pass scoring."""
    description = attribution or f"{title} rock band performing live at concert"
    return CommonsImageInfo(
        commons_file=commons_file,
        image_url="https://example.com/full.jpg",
        thumbnail_url="https://example.com/thumb.jpg",
        license="CC BY 2.0",
        license_url="https://creativecommons.org/licenses/by/2.0/",
        author="User:Example",
        source_url=f"https://commons.wikimedia.org/wiki/File:{commons_file}",
        attribution_text=description,
        title=title,
        imageinfo={
            "extmetadata": {
                "ImageDescription": {"value": description},
                "ObjectName": {"value": title},
            },
        },
    )


def test_resolve_artist_image_returns_ok_record(monkeypatch) -> None:
    """A full successful chain yields an ok cache record."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: "Q42",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_filename",
        lambda _qid: "Example Artist.jpg",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_image_info",
        lambda _filename: _music_commons_info(
            commons_file="Example Artist.jpg",
            title="Example Artist live concert",
        ),
    )

    record = resolve_artist_image(
        artist_mbid="mbid-1",
        artist_name="Example Artist",
    )

    assert record.status == "ok"
    assert record.thumbnail_url == "https://example.com/thumb.jpg"
    assert record.wikidata_id == "Q42"


def test_resolve_artist_image_records_missing_wikidata(monkeypatch) -> None:
    """Missing Wikidata links fall back to Commons search when that also fails."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_wikidata_id_by_musicbrainz_mbid",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_alias_names",
        lambda _mbid: [],
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_disambiguation",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda *_args, **_kwargs: None,
    )

    record = resolve_artist_image(
        artist_mbid="mbid-2",
        artist_name="No Wikidata",
    )

    assert record.status == "not_found"
    assert record.reason == "no_wikidata_id"


def test_resolve_artist_image_uses_commons_search_fallback(monkeypatch) -> None:
    """When Wikidata and Wikipedia have no image, Commons search can still succeed."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_wikidata_id_by_musicbrainz_mbid",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_alias_names",
        lambda _mbid: [],
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_disambiguation",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda _name, context=None: _music_commons_info(
            commons_file="Francis of Delirium (2024) 1.jpg",
            title="Francis of Delirium",
        ),
    )

    record = resolve_artist_image(
        artist_mbid="mbid-3",
        artist_name="Francis of Delirium",
    )

    assert record.status == "ok"
    assert record.thumbnail_url == "https://example.com/thumb.jpg"
    assert record.commons_file == "Francis of Delirium (2024) 1.jpg"


def test_resolve_artist_image_uses_wikipedia_fallback(monkeypatch) -> None:
    """Wikipedia article images are preferred over noisy Commons search hits."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_wikidata_id_by_musicbrainz_mbid",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_alias_names",
        lambda _mbid: [],
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_disambiguation",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda _names, disambiguation=None, context=None: (
            _music_commons_info(
                commons_file="The Memorials.jpg",
                title="The Memorials",
            ),
            "Q7750962",
        ),
    )

    def _fail_commons_search(*_args, **_kwargs) -> CommonsImageInfo:
        raise AssertionError("commons search should not run")

    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        _fail_commons_search,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_info_by_mbid",
        lambda _mbid: None,
    )

    record = resolve_artist_image(
        artist_mbid="mbid-memorials",
        artist_name="Memorials",
    )

    assert record.status == "ok"
    assert record.commons_file == "The Memorials.jpg"
    assert record.wikidata_id == "Q7750962"


def test_resolve_artist_image_uses_name_only_fallback_when_musicbrainz_missing(
    monkeypatch,
) -> None:
    """Artists missing from MusicBrainz can still resolve via Wikipedia or Commons."""
    monkeypatch.setenv("ARTIST_IMAGE_MIN_CONFIDENCE_NAME", "60")
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_info",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda _name, context=None: _music_commons_info(
            commons_file="Sibylle Kefer 2019.jpg",
            title="Sibylle Kefer",
            attribution="Sibylle Kefer musician performing live at concert festival",
        ),
    )

    record = resolve_artist_image(artist_name="Sibylle Kefer")

    assert record.status == "ok"
    assert record.artist_mbid == ""
    assert record.artist_name == "Sibylle Kefer"
    assert record.commons_file == "Sibylle Kefer 2019.jpg"


def test_resolve_artist_image_rejects_wikidata_image_without_artist_name(
    monkeypatch,
) -> None:
    """Wikidata portraits are rejected when the Commons file names another artist."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: "Q123",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_filename",
        lambda _qid: "Comet Gain Popfest 2012.jpg",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_image_info",
        lambda _filename: CommonsImageInfo(
            commons_file="Comet Gain Popfest 2012.jpg",
            image_url="https://example.com/full.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            license="CC BY 2.0",
            license_url="https://creativecommons.org/licenses/by/2.0/",
            author="User:Example",
            source_url="https://commons.wikimedia.org/wiki/File:Comet_Gain.jpg",
            attribution_text="Comet Gain at London Popfest",
            title="Comet Gain at London Popfest",
        ),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver._resolve_wikipedia_fallback",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda *_args, **_kwargs: None,
    )

    record = resolve_artist_image(
        artist_mbid="mbid-clientele",
        artist_name="The Clientele",
    )

    assert record.status == "not_found"
    assert record.reason == "low_confidence"


def test_resolve_artist_image_skips_musicbrainz_homonym_for_short_names(
    monkeypatch,
) -> None:
    """Ambiguous short names must not resolve to unrelated MusicBrainz artists."""
    from music_review.pipeline.enrichment.musicbrainz_client import ArtistInfo

    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_info",
        lambda _name: ArtistInfo(
            mbid="mbid-nancy",
            name="Nancy Wilson",
            country="US",
            artist_type="Person",
            disambiguation=None,
            tags=[],
            members=[],
        ),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: (_ for _ in ()).throw(AssertionError("wikidata should not run")),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda *_args, **_kwargs: None,
    )

    record = resolve_artist_image(artist_name="Sue")

    assert record.status == "not_found"
    assert record.artist_name == "Sue"
    assert record.artist_mbid == ""


def test_resolve_artist_image_uses_member_fallback_for_groups(monkeypatch) -> None:
    """Groups may use distinctive member photos when direct lookup fails."""
    from music_review.pipeline.enrichment.commons_image_confidence import ArtistContext

    monkeypatch.setenv("ARTIST_IMAGE_MIN_CONFIDENCE_MEMBER", "60")
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_wikidata_id_by_musicbrainz_mbid",
        lambda _mbid: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver._resolve_wikipedia_fallback",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda name, context=None: (
            _music_commons_info(
                commons_file="Thom Yorke live.jpg",
                title="Thom Yorke",
            )
            if context is not None and context.depicts_member_name == "Thom Yorke"
            else None
        ),
    )

    record = resolve_artist_image(
        artist_mbid="mbid-radiohead",
        artist_name="Radiohead",
        context=ArtistContext(
            artist_mbid="mbid-radiohead",
            artist_type="Group",
            artist_members=("Thom Yorke",),
        ),
    )

    assert record.status == "ok"
    assert record.resolution_source == "member_fallback"
    assert record.depicts_member_name == "Thom Yorke"
