"""Tests for scraper storage (JSONL read/write of reviews)."""

from __future__ import annotations

from pathlib import Path

from music_review.domain.models import Review, Track
from music_review.pipeline.scraper.storage import (
    append_review,
    load_corpus,
    load_existing_ids,
    write_corpus,
)


def _make_review(review_id: int, artist: str = "Artist", album: str = "Album") -> Review:
    return Review(
        id=review_id,
        url=f"https://example.com/{review_id}",
        artist=artist,
        album=album,
        text="Review text.",
    )


def test_append_review_adds_one_line(tmp_path: Path) -> None:
    """append_review appends a single JSON line to the file."""
    path = tmp_path / "reviews.jsonl"
    r = _make_review(1)
    append_review(path, r)
    append_review(path, _make_review(2, "B", "C"))
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert "1" in lines[0] and "Artist" in lines[0]
    assert "2" in lines[1] and "B" in lines[1]


def test_load_existing_ids_returns_set_of_ids(tmp_path: Path) -> None:
    """load_existing_ids returns the set of all review IDs in the file."""
    path = tmp_path / "reviews.jsonl"
    append_review(path, _make_review(10))
    append_review(path, _make_review(20))
    append_review(path, _make_review(10))
    assert load_existing_ids(path) == {10, 20}


def test_load_existing_ids_empty_file_returns_empty_set(tmp_path: Path) -> None:
    """An empty or missing file yields an empty set of IDs."""
    path = tmp_path / "empty.jsonl"
    path.touch()
    assert load_existing_ids(path) == set()
    assert load_existing_ids(tmp_path / "nonexistent.jsonl") == set()


def test_load_corpus_returns_id_to_dict(tmp_path: Path) -> None:
    """load_corpus returns a mapping of review ID to raw dict; later lines overwrite."""
    path = tmp_path / "corpus.jsonl"
    append_review(path, _make_review(1, "A", "B"))
    append_review(path, _make_review(1, "A2", "B2"))
    append_review(path, _make_review(2, "C", "D"))
    corpus = load_corpus(path)
    assert corpus[1]["artist"] == "A2"
    assert corpus[2]["artist"] == "C"


def test_write_corpus_overwrites_file(tmp_path: Path) -> None:
    """write_corpus writes the full list of review dicts; file is overwritten."""
    path = tmp_path / "out.jsonl"
    append_review(path, _make_review(99))
    corpus = [
        {"id": 1, "artist": "X", "album": "Y", "url": "u", "text": "t"},
        {"id": 2, "artist": "Z", "album": "W", "url": "u2", "text": "t2"},
    ]
    write_corpus(path, corpus)
    ids = load_existing_ids(path)
    assert ids == {1, 2}
    assert load_corpus(path)[1]["artist"] == "X"
