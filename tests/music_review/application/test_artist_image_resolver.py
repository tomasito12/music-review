"""Tests for artist image resolver orchestration."""

from __future__ import annotations

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.application.artist_image_resolver import resolve_artist_image


def test_resolve_artist_image_returns_ok_record(monkeypatch) -> None:
    """A full successful chain yields an ok cache record."""
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_wikidata_id",
        lambda _mbid: "Q42",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_filename",
        lambda _qid: "Example.jpg",
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_commons_image_info",
        lambda _filename: CommonsImageInfo(
            commons_file="Example.jpg",
            image_url="https://example.com/full.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            license="CC BY 2.0",
            license_url="https://creativecommons.org/licenses/by/2.0/",
            author="User:Example",
            source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
            attribution_text="credit",
            title="Example",
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
        lambda _names, disambiguation=None: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda _name: None,
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
        lambda _names, disambiguation=None: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda _name: CommonsImageInfo(
            commons_file="Francis of Delirium (2024) 1.jpg",
            image_url="https://example.com/full.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            license="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            author="User:Example",
            source_url="https://commons.wikimedia.org/wiki/File:Francis_of_Delirium.jpg",
            attribution_text="credit",
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
        lambda _names, disambiguation=None: (
            CommonsImageInfo(
                commons_file="The Memorials.jpg",
                image_url="https://example.com/full.jpg",
                thumbnail_url="https://example.com/thumb.jpg",
                license="CC BY 3.0",
                license_url="https://creativecommons.org/licenses/by/3.0/",
                author="User:Example",
                source_url="https://commons.wikimedia.org/wiki/File:The_Memorials.jpg",
                attribution_text="credit",
                title="The Memorials",
            ),
            "Q7750962",
        ),
    )

    def _fail_commons_search(_name: str) -> CommonsImageInfo:
        raise AssertionError("commons search should not run")

    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        _fail_commons_search,
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
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.fetch_artist_info",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_via_wikipedia",
        lambda _names, disambiguation=None: (None, None),
    )
    monkeypatch.setattr(
        "music_review.application.artist_image_resolver.find_commons_image_by_artist_name",
        lambda _name: CommonsImageInfo(
            commons_file="Sibylle Kefer 2019.jpg",
            image_url="https://example.com/full.jpg",
            thumbnail_url="https://example.com/thumb.jpg",
            license="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            author="User:Example",
            source_url="https://commons.wikimedia.org/wiki/File:Sibylle_Kefer.jpg",
            attribution_text="credit",
            title="Sibylle Kefer",
        ),
    )

    record = resolve_artist_image(artist_name="Sibylle Kefer")

    assert record.status == "ok"
    assert record.artist_mbid == ""
    assert record.artist_name == "Sibylle Kefer"
    assert record.commons_file == "Sibylle Kefer 2019.jpg"
