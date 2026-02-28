"""Tests for plattentests.de HTML review parser."""

from __future__ import annotations

from datetime import date

from music_review.pipeline.scraper.parser import parse_review


# Minimal valid HTML structure matching the plattentests.de layout (see parser docstrings).
MINIMAL_REVIEW_HTML = """
<div id="rezension">
  <div class="headerbox">
    <h1>Artist Name - Album Title</h1>
    <p>Sony<br>VÖ: 26.09.2025</p>
    <p class="bewertung b8">Unsere Bewertung: <strong>8/10</strong></p>
    <p class="bewertung b7">Eure Ø-Bewertung: <strong>7/10</strong></p>
  </div>
  <div id="rezitext">
    <h2>Review Title</h2>
    <p class="autor">(Max Mustermann)</p>
    <p>First paragraph of the review.</p>
    <p>Second paragraph.</p>
  </div>
</div>
"""


def test_parse_review_extracts_artist_album_and_text() -> None:
    """parse_review extracts artist, album, and body text from the minimal layout."""
    review = parse_review(42, MINIMAL_REVIEW_HTML)
    assert review is not None
    assert review.id == 42
    assert review.artist == "Artist Name"
    assert review.album == "Album Title"
    assert review.text == "First paragraph of the review.\n\nSecond paragraph."
    assert review.url == "https://www.plattentests.de/rezi.php?show=42"


def test_parse_review_extracts_title_author_ratings_and_date() -> None:
    """parse_review extracts optional title, author, ratings, and release date."""
    review = parse_review(1, MINIMAL_REVIEW_HTML)
    assert review is not None
    assert review.title == "Review Title"
    assert review.author == "Max Mustermann"
    assert review.rating == 8.0
    assert review.user_rating == 7.0
    assert review.release_date == date(2025, 9, 26)
    assert review.release_year == 2025
    assert "Sony" in review.labels


def test_parse_review_returns_none_when_rezension_container_missing() -> None:
    """parse_review returns None when the page has no #rezension container."""
    html = "<html><body><div>No rezension here</div></body></html>"
    assert parse_review(99, html) is None


def test_parse_review_returns_none_when_core_fields_missing() -> None:
    """parse_review returns None when artist, album, or body text is missing."""
    # Headerbox with h1 but no " - " (no artist/album split); still has rezitext
    html = """
    <div id="rezension">
      <div class="headerbox"><h1>Only Album</h1></div>
      <div id="rezitext"><p>Body</p></div>
    </div>
    """
    # Parser might return None or a review depending on _parse_artist_album handling.
    # If artist is None, the parser returns None due to "if not artist or not album or not body_text"
    result = parse_review(1, html)
    # With "Only Album" we get album="Only Album", artist=None -> None
    assert result is None


def test_parse_review_with_tracklist_and_highlights() -> None:
    """parse_review extracts tracklist, highlights, and total duration when present."""
    # Highlight names must match track titles (case-insensitive) for is_highlight to be set.
    html = """
    <div id="rezension">
      <div class="headerbox">
        <h1>Band - Record</h1>
        <p>Label</p>
      </div>
      <div id="rezitext">
        <p>Review body text.</p>
      </div>
      <div id="rezihighlights">
        <ul><li>Track One</li><li>Track Two</li></ul>
      </div>
      <div id="rezitracklist">
        <p>Gesamtspielzeit: 45:00 min.</p>
        <ul>
          <li><ol><li>Track One</li><li>Track Two</li></ol></li>
        </ul>
      </div>
    </div>
    """
    review = parse_review(10, html)
    assert review is not None
    assert review.total_duration == "45:00"
    assert review.highlights == ["Track One", "Track Two"]
    assert len(review.tracklist) == 2
    assert review.tracklist[0].title == "Track One"
    assert review.tracklist[1].title == "Track Two"
    # Parser sets is_highlight when the track title appears in the highlights list.
    assert review.tracklist[0].is_highlight is True
    assert review.tracklist[1].is_highlight is True


def test_parse_review_references() -> None:
    """parse_review extracts reference links from #reziref."""
    html = """
    <div id="rezension">
      <div class="headerbox"><h1>A - B</h1><p>X</p></div>
      <div id="rezitext"><p>Text.</p></div>
      <div id="reziref">
        <h4>Referenzen</h4>
        <p><a href="#">Tweedy</a>; <a href="#">Wilco</a>;</p>
      </div>
    </div>
    """
    review = parse_review(1, html)
    assert review is not None
    assert review.references == ["Tweedy", "Wilco"]
