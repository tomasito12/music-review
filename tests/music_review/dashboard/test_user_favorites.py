"""Tests for saved album bookmarks in the user database."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_review.dashboard.user_db import (
    UserFavoriteInput,
    add_user_favorite,
    create_user_with_email,
    get_connection,
    list_user_favorites,
    merge_user_favorites,
    remove_user_favorite,
)


@pytest.fixture()
def db(tmp_path: Path):
    """Fresh SQLite connection per test."""
    return get_connection(tmp_path / "test.db")


def _favorite(
    review_id: int,
    *,
    artist: str = "Artist",
    album: str = "Album",
    saved_at: str | None = None,
) -> UserFavoriteInput:
    """Build one favorite input row."""
    return UserFavoriteInput(
        review_id=review_id,
        artist=artist,
        album=album,
        review_url=f"https://example.com/{review_id}",
        source="archive",
        saved_at=saved_at,
    )


def test_list_user_favorites_returns_empty_for_new_user(db) -> None:
    """A user without bookmarks returns an empty list."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    assert list_user_favorites(db, slug) == []


def test_add_user_favorite_persists_snapshot(db) -> None:
    """Saving one album stores the snapshot fields."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    add_user_favorite(db, slug, _favorite(42, artist="Alpha", album="First"))

    rows = list_user_favorites(db, slug)
    assert len(rows) == 1
    assert rows[0]["review_id"] == 42
    assert rows[0]["artist"] == "Alpha"
    assert rows[0]["album"] == "First"
    assert rows[0]["review_url"] == "https://example.com/42"
    assert rows[0]["source"] == "archive"
    assert rows[0]["saved_at"]


def test_add_user_favorite_is_idempotent(db) -> None:
    """Saving the same review twice keeps the first saved_at timestamp."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    first = _favorite(7, saved_at="2026-01-01T10:00:00Z")
    second = _favorite(7, artist="Changed", saved_at="2026-06-01T10:00:00Z")
    add_user_favorite(db, slug, first)
    add_user_favorite(db, slug, second)

    rows = list_user_favorites(db, slug)
    assert len(rows) == 1
    assert rows[0]["artist"] == "Artist"
    assert rows[0]["saved_at"] == "2026-01-01T10:00:00Z"


def test_remove_user_favorite_deletes_row(db) -> None:
    """Removing a saved album deletes only that row."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    add_user_favorite(db, slug, _favorite(1))
    add_user_favorite(db, slug, _favorite(2))

    removed = remove_user_favorite(db, slug, 1)
    assert removed is True
    rows = list_user_favorites(db, slug)
    assert [row["review_id"] for row in rows] == [2]


def test_remove_user_favorite_returns_false_when_missing(db) -> None:
    """Removing an unknown favorite returns False."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    assert remove_user_favorite(db, slug, 99) is False


def test_merge_user_favorites_inserts_only_new_rows(db) -> None:
    """Merge adds local rows without overwriting existing server rows."""
    slug = create_user_with_email(db, "alice@example.com", "secret123")
    assert slug is not None
    add_user_favorite(
        db,
        slug,
        _favorite(1, artist="Server", saved_at="2026-01-01T10:00:00Z"),
    )

    merged = merge_user_favorites(
        db,
        slug,
        [
            _favorite(1, artist="Local", saved_at="2026-06-01T10:00:00Z"),
            _favorite(2, artist="Local Two", saved_at="2026-06-02T10:00:00Z"),
        ],
    )

    assert merged == 1
    rows = list_user_favorites(db, slug)
    by_id = {row["review_id"]: row for row in rows}
    assert by_id[1]["artist"] == "Server"
    assert by_id[1]["saved_at"] == "2026-01-01T10:00:00Z"
    assert by_id[2]["artist"] == "Local Two"
