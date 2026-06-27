"""Tests for English Wikipedia artist image fallback."""

from __future__ import annotations

from music_review.application.artist_image_models import CommonsImageInfo
from music_review.pipeline.enrichment.wikipedia_client import (
    _commons_filename_from_page,
    _commons_filename_from_upload_url,
    build_wikipedia_search_names,
    find_commons_image_via_wikipedia,
)


def test_build_wikipedia_search_names_adds_the_prefix_variant() -> None:
    """Search names include a ``The …`` variant for bare artist names."""
    names = build_wikipedia_search_names("Memorials", alias_names=["The Memoreals"])

    assert "Memorials" in names
    assert "The Memorials" in names
    assert "The Memoreals" in names


def test_commons_filename_from_upload_url_parses_commons_path() -> None:
    """Commons filenames are parsed from standard upload URLs."""
    filename = _commons_filename_from_upload_url(
        "https://upload.wikimedia.org/wikipedia/commons/3/3f/The_Memorials.jpg",
    )

    assert filename == "The Memorials.jpg"


def test_commons_filename_from_page_prefers_page_image_free() -> None:
    """Wikipedia pageprops provide the primary free image filename."""
    filename = _commons_filename_from_page(
        {
            "pageprops": {"page_image_free": "The_Memorials.jpg"},
            "original": {
                "source": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Other.jpg",
            },
        },
    )

    assert filename == "The Memorials.jpg"


def test_find_commons_image_via_wikipedia_returns_licensed_image(monkeypatch) -> None:
    """A matching Wikipedia article can supply a Commons image."""
    monkeypatch.setattr(
        "music_review.pipeline.enrichment.wikipedia_client._search_wikipedia",
        lambda _query, limit=5: [
            {
                "title": "The Memorials",
                "snippet": "American hard rock <span>band</span>",
            },
        ],
    )
    monkeypatch.setattr(
        "music_review.pipeline.enrichment.wikipedia_client._fetch_wikipedia_page",
        lambda _title: {
            "pageprops": {
                "page_image_free": "The_Memorials.jpg",
                "wikibase_item": "Q7750962",
            },
        },
    )
    monkeypatch.setattr(
        "music_review.pipeline.enrichment.wikipedia_client.fetch_commons_image_info",
        lambda _filename: CommonsImageInfo(
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
    )

    info, wikidata_id = find_commons_image_via_wikipedia(["Memorials"])

    assert info is not None
    assert info.commons_file == "The Memorials.jpg"
    assert wikidata_id == "Q7750962"
