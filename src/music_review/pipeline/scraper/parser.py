from __future__ import annotations

import logging
import re
from datetime import date

from bs4 import BeautifulSoup, Tag

from music_review.pipeline.scraper.models import Review, Track

logger = logging.getLogger(__name__)


def parse_review(review_id: int, html: str) -> Review | None:
    """Parse a plattentests.de review HTML into a Review object.

    This version is tailored to the modern layout (e.g. ID 21235).
    Returns None if required core fields (artist, album, text) are missing.
    """
    soup = BeautifulSoup(html, "lxml")

    container = soup.find("div", id="rezension")
    if container is None:
        logger.warning("No rezension container found for id=%s", review_id)
        return None

    (
        artist,
        album,
        labels,
        release_date,
        release_year,
        rating,
        user_rating,
    ) = _parse_header(container)

    title, author, body_text = _parse_text_block(container)

    tracklist, highlights, total_duration = _parse_track_and_highlights(container)
    references = _parse_references(container)

    if not artist or not album or not body_text:
        logger.warning(
            "Skipping review %s due to missing core fields "
            "(artist=%r, album=%r, text_length=%s).",
            review_id,
            artist,
            album,
            len(body_text) if body_text else 0,
        )
        return None

    url = f"https://www.plattentests.de/rezi.php?show={review_id}"

    return Review(
        id=review_id,
        url=url,
        artist=artist,
        album=album,
        text=body_text,
        title=title,
        author=author,
        labels=labels,
        release_date=release_date,
        release_year=release_year,
        rating=rating,
        user_rating=user_rating,
        tracklist=tracklist,
        highlights=highlights,
        total_duration=total_duration,
        references=references,
        raw_html=None,  # set to html if you want to store full HTML
    )


# ---------------------------------------------------------------------------
# Header: Artist, Album, Label, Release, Ratings
# ---------------------------------------------------------------------------


def _parse_header(
        container: Tag,
) -> tuple[str | None, str | None, list[str], date | None, int | None, float | None, float | None]:
    """Parse the header box with artist/album, label, release and ratings."""
    header_box = _find_header_box(container)

    if header_box is None:
        return None, None, [], None, None, None, None

    artist, album = _parse_artist_album(header_box)
    labels, release_date, release_year = _parse_label_and_release(header_box)
    rating, user_rating = _parse_ratings(header_box)

    return artist, album, labels, release_date, release_year, rating, user_rating


def _find_header_box(container: Tag) -> Tag | None:
    """Find the headerbox that contains the main <h1>."""
    for div in container.find_all("div", class_="headerbox"):
        if div.find("h1"):
            return div
    return None


def _parse_artist_album(header_box: Tag) -> tuple[str | None, str | None]:
    """Parse artist and album from the <h1> 'Artist - Album'."""
    heading = header_box.find("h1")
    if not heading:
        return None, None

    text = heading.get_text(strip=True)
    if " - " in text:
        artist, album = text.split(" - ", 1)
        return artist.strip() or None, album.strip() or None

    # Fallback: whole heading is album
    return None, text.strip() or None


def _parse_references(container: Tag) -> list[str]:
    """Parse the 'Referenzen' block into a list of names.

    Example HTML (simplified):

        <div id="reziref">
            <h4>Referenzen</h4>
            <p>
                <a href="suche.php?...">Tweedy</a>;
                <a href="suche.php?...">Wilco</a>;
                ...
            </p>
        </div>
    """
    ref_div = container.find("div", id="reziref")
    if ref_div is None:
        return []

    names: list[str] = []
    for link in ref_div.find_all("a"):
        text = link.get_text(strip=True)
        if text:
            names.append(text)

    # Deduplicate while preserving order (case-insensitive)
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(name)

    return unique


def _parse_label_and_release(
        header_box: Tag,
) -> tuple[list[str], date | None, int | None]:
    """Parse label(s) and release date/year from the first non-rating <p>."""
    info_p: Tag | None = None

    for p in header_box.find_all("p"):
        classes = p.get("class") or []
        if "bewertung" not in classes:
            info_p = p
            break

    if info_p is None:
        return [], None, None

    # Example HTML:
    # <p>Sony <br>VÖ: 26.09.2025</p>
    parts = list(info_p.stripped_strings)
    labels: list[str] = []
    rel_date: date | None = None
    rel_year: int | None = None

    if parts:
        labels = _split_labels(parts[0])

    for part in parts[1:]:
        d, y = _extract_date_and_year_from_text(part)
        if d:
            rel_date = d
        if y:
            rel_year = y

    # If we have a date but no explicit year, derive it
    if rel_date and rel_year is None:
        rel_year = rel_date.year

    return labels, rel_date, rel_year


def _parse_ratings(header_box: Tag) -> tuple[float | None, float | None]:
    """Extract 'Unsere Bewertung' and 'Eure Ø-Bewertung' from the header box.

    Works for markup like:
        <p class="bewertung b8">Unsere Bewertung: <strong>8/10</strong></p>
        <p class="bewertung b7">Eure Ø-Bewertung: <strong>7/10</strong></p>
    """
    rating: float | None = None
    user_rating: float | None = None

    def has_bewertung(cls: object) -> bool:
        # cls can be a string ("bewertung b8") or a list (["bewertung", "b8"])
        if cls is None:
            return False
        if isinstance(cls, str):
            classes = cls.split()
        elif isinstance(cls, list):
            classes = [str(c) for c in cls]
        else:
            return False
        return "bewertung" in classes

    for p in header_box.find_all("p", class_=has_bewertung):
        text = p.get_text(" ", strip=True)
        strong = p.find("strong")
        if not strong:
            continue

        value = _parse_rating_value(strong.get_text(strip=True))
        if value is None:
            continue

        if "Unsere" in text:
            rating = value
        elif "Eure" in text:
            user_rating = value

    return rating, user_rating


# ---------------------------------------------------------------------------
# Textblock: Review title (h2), author, body text
# ---------------------------------------------------------------------------


def _parse_text_block(
        container: Tag,
) -> tuple[str | None, str | None, str | None]:
    """Parse review title (h2), author and main body text from #rezitext."""
    text_div = container.find("div", id="rezitext")
    if text_div is None:
        return None, None, None

    # Review title is the <h2> in rezitext, e.g. "American Abgrund"
    title_tag = text_div.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Author is in <p class="autor">(<a>Author Name</a>)</p>
    author: str | None = None
    author_p = text_div.find("p", class_="autor")
    if author_p:
        author_text = author_p.get_text(strip=True)
        author = author_text.strip("() ").strip() if author_text else None

    # Body: all <p> in rezitext except the author paragraph
    paragraphs: list[str] = []
    for p in text_div.find_all("p"):
        classes = p.get("class") or []
        if "autor" in classes:
            continue
        text = p.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)

    body_text = "\n\n".join(paragraphs) if paragraphs else None
    return title, author, body_text


# ---------------------------------------------------------------------------
# Tracklist, Highlights, Total Duration
# ---------------------------------------------------------------------------


def _parse_track_and_highlights(
        container: Tag,
) -> tuple[list[Track], list[str], str | None]:
    """Parse tracklist, highlight tracks and total duration."""
    tracks: list[Track] = []
    highlights: list[str] = []
    total_duration: str | None = None

    # Highlights: <div id="rezihighlights"><ul><li>...</li>...</ul></div>
    highlights_div = container.find("div", id="rezihighlights")
    if highlights_div:
        for li in highlights_div.find_all("li"):
            name = li.get_text(strip=True)
            if name:
                highlights.append(name)

    # Tracklist + total duration: <div id="rezitracklist">
    tracklist_div = container.find("div", id="rezitracklist")
    if tracklist_div:
        # Gesamtspielzeit: 111:35 min.
        duration_p = tracklist_div.find("p")
        if duration_p:
            m = re.search(r"(\d{1,3}:\d{2})", duration_p.get_text(" ", strip=True))
            if m:
                total_duration = m.group(1)

        ul = tracklist_div.find("ul")
        track_no = 1
        if ul:
            # Each top-level <li> is a CD ("CD 1") containing an <ol> with tracks
            for li_disc in ul.find_all("li", recursive=False):
                ol = li_disc.find("ol")
                if not ol:
                    continue
                for li_track in ol.find_all("li"):
                    text = li_track.get_text(" ", strip=True)
                    if not text:
                        continue
                    title = text
                    tracks.append(
                        Track(
                            number=track_no,
                            title=title,
                            duration=None,
                            is_highlight=False,
                        ),
                    )
                    track_no += 1

        else:
            ol = tracklist_div.find("ol")
            if ol:
                for li_track in ol.find_all("li"):
                    text = li_track.get_text(" ", strip=True)
                    if not text:
                        continue
                    tracks.append(
                        Track(
                            number=track_no,
                            title=text,
                            duration=None,
                            is_highlight=False,
                        ),
                    )
                    track_no += 1

    # Mark highlights in tracks by title match (case-insensitive)
    if tracks and highlights:
        highlight_set = {h.lower() for h in highlights}
        for t in tracks:
            if t.title.lower() in highlight_set:
                t.is_highlight = True

    return tracks, highlights, total_duration


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _split_labels(raw: str) -> list[str]:
    """Split a label string like 'Sony / Sub Label' into a list."""
    parts = re.split(r"[\/,;]", raw)
    return [p.strip() for p in parts if p.strip()]


def _extract_date_and_year_from_text(
        text: str,
) -> tuple[date | None, int | None]:
    """Extract a date and/or year from a text like 'VÖ: 26.09.2025'."""
    text = text.strip()

    # DD.MM.YYYY
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        day_s, month_s, year_s = m.groups()
        try:
            d = date(int(year_s), int(month_s), int(day_s))
            return d, d.year
        except ValueError:
            return None, int(year_s)

    # Fallback: just a 4-digit year
    m_year = re.search(r"\b(\d{4})\b", text)
    if m_year:
        year = int(m_year.group(1))
        return None, year

    return None, None


def _parse_rating_value(raw: str) -> float | None:
    """Parse rating values like '8/10' or '7,5/10' into a float."""
    m = re.match(r"(\d+(?:[.,]\d+)?)", raw)
    if not m:
        return None
    val_str = m.group(1).replace(",", ".")
    try:
        return float(val_str)
    except ValueError:
        return None
