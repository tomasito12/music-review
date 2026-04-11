"""Tests for the SQLite user store (CRUD, authentication, sessions)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from music_review.dashboard.user_db import (
    authenticate_user,
    change_password,
    clear_spotify_credentials,
    create_session_token,
    create_user,
    delete_all_sessions_for_user,
    delete_session_token,
    get_connection,
    list_user_slugs,
    load_spotify_credentials,
    load_spotify_last_preview_at,
    load_user_profile,
    purge_expired_sessions,
    save_spotify_credentials,
    save_spotify_last_preview_at,
    save_user_profile,
    user_exists,
    validate_session_token,
)


@pytest.fixture()
def db(tmp_path: Path):
    """Fresh in-memory-like SQLite connection per test."""
    db_path = tmp_path / "test.db"
    return get_connection(db_path)


class TestUserCRUD:
    def test_create_and_authenticate(self, db):
        assert create_user(db, "alice", "secret123")
        assert authenticate_user(db, "alice", "secret123")

    def test_create_duplicate_returns_false(self, db):
        create_user(db, "alice", "pw1")
        assert create_user(db, "alice", "pw2") is False

    def test_authenticate_wrong_password(self, db):
        create_user(db, "alice", "correct")
        assert authenticate_user(db, "alice", "wrong") is False

    def test_authenticate_nonexistent_user(self, db):
        assert authenticate_user(db, "ghost", "pw") is False

    def test_user_exists_true_and_false(self, db):
        assert user_exists(db, "nobody") is False
        create_user(db, "bob", "pw")
        assert user_exists(db, "bob") is True

    def test_change_password_succeeds(self, db):
        create_user(db, "alice", "old")
        assert change_password(db, "alice", "new")
        assert authenticate_user(db, "alice", "new")
        assert authenticate_user(db, "alice", "old") is False

    def test_change_password_nonexistent_returns_false(self, db):
        assert change_password(db, "ghost", "pw") is False

    def test_list_user_slugs_sorted(self, db):
        create_user(db, "zara", "pw")
        create_user(db, "alice", "pw")
        assert list_user_slugs(db) == ["alice", "zara"]

    def test_list_user_slugs_empty(self, db):
        assert list_user_slugs(db) == []


class TestProfileData:
    def test_save_and_load_roundtrip(self, db):
        create_user(db, "alice", "pw")
        data = {"filter_settings": {"year_min": 2000}, "communities": ["C01"]}
        save_user_profile(db, "alice", data)
        loaded = load_user_profile(db, "alice")
        assert loaded is not None
        assert loaded["filter_settings"]["year_min"] == 2000

    def test_load_nonexistent_user_returns_none(self, db):
        assert load_user_profile(db, "ghost") is None

    def test_load_empty_profile_returns_none(self, db):
        create_user(db, "alice", "pw")
        assert load_user_profile(db, "alice") is None


class TestSpotifyPreview:
    def test_save_and_load_preview_timestamp(self, db):
        create_user(db, "alice", "pw")
        save_spotify_last_preview_at(db, "alice", "2024-06-01T12:00:00Z")
        assert load_spotify_last_preview_at(db, "alice") == "2024-06-01T12:00:00Z"

    def test_load_preview_nonexistent_user(self, db):
        assert load_spotify_last_preview_at(db, "ghost") is None

    def test_load_preview_no_value_yet(self, db):
        create_user(db, "alice", "pw")
        assert load_spotify_last_preview_at(db, "alice") is None


class TestSpotifyCredentials:
    def test_save_and_load_roundtrip(self, db):
        create_user(db, "alice", "pw")
        save_spotify_credentials(db, "alice", "my-client-id", "my-secret")
        result = load_spotify_credentials(db, "alice")
        assert result == ("my-client-id", "my-secret")

    def test_load_returns_none_when_not_set(self, db):
        create_user(db, "alice", "pw")
        assert load_spotify_credentials(db, "alice") is None

    def test_load_returns_none_for_nonexistent_user(self, db):
        assert load_spotify_credentials(db, "ghost") is None

    def test_clear_removes_credentials(self, db):
        create_user(db, "alice", "pw")
        save_spotify_credentials(db, "alice", "cid", "csec")
        clear_spotify_credentials(db, "alice")
        assert load_spotify_credentials(db, "alice") is None

    def test_save_trims_whitespace(self, db):
        create_user(db, "alice", "pw")
        save_spotify_credentials(db, "alice", "  cid  ", "  csec  ")
        result = load_spotify_credentials(db, "alice")
        assert result == ("cid", "csec")

    def test_overwrite_existing_credentials(self, db):
        create_user(db, "alice", "pw")
        save_spotify_credentials(db, "alice", "old-id", "old-secret")
        save_spotify_credentials(db, "alice", "new-id", "new-secret")
        result = load_spotify_credentials(db, "alice")
        assert result == ("new-id", "new-secret")

    def test_load_returns_none_when_only_client_id_set(self, db):
        create_user(db, "alice", "pw")
        db.execute(
            "UPDATE users SET spotify_client_id = ? WHERE slug = ?",
            ("cid", "alice"),
        )
        db.commit()
        assert load_spotify_credentials(db, "alice") is None


class TestSessionTokens:
    def test_create_and_validate(self, db):
        create_user(db, "alice", "pw")
        token = create_session_token(db, "alice")
        assert isinstance(token, str)
        assert len(token) > 32
        slug = validate_session_token(db, token)
        assert slug == "alice"

    def test_validate_invalid_token(self, db):
        assert validate_session_token(db, "nonexistent") is None

    def test_delete_token(self, db):
        create_user(db, "alice", "pw")
        token = create_session_token(db, "alice")
        delete_session_token(db, token)
        assert validate_session_token(db, token) is None

    def test_delete_all_sessions(self, db):
        create_user(db, "alice", "pw")
        t1 = create_session_token(db, "alice")
        t2 = create_session_token(db, "alice")
        delete_all_sessions_for_user(db, "alice")
        assert validate_session_token(db, t1) is None
        assert validate_session_token(db, t2) is None

    def test_expired_token_returns_none(self, db):
        create_user(db, "alice", "pw")
        token = create_session_token(db, "alice", lifetime_days=0)
        db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            (
                (datetime.now(UTC) - timedelta(hours=1))
                .isoformat()
                .replace("+00:00", "Z"),
                token,
            ),
        )
        db.commit()
        assert validate_session_token(db, token) is None

    def test_purge_expired_sessions(self, db):
        create_user(db, "alice", "pw")
        token = create_session_token(db, "alice")
        db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            ("2020-01-01T00:00:00Z", token),
        )
        db.commit()
        removed = purge_expired_sessions(db)
        assert removed == 1
        assert validate_session_token(db, token) is None
