"""Tests for the SQLite user store (CRUD, authentication, sessions)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from music_review.dashboard.spotify_oauth_token_json import spotify_token_to_json_str
from music_review.dashboard.user_db import (
    authenticate_user,
    change_password,
    clear_deezer_credentials,
    clear_deezer_oauth_token,
    clear_spotify_credentials,
    clear_spotify_oauth_token,
    create_session_token,
    create_user,
    delete_all_sessions_for_user,
    delete_session_token,
    get_connection,
    list_user_slugs,
    load_deezer_credentials,
    load_deezer_last_preview_at,
    load_deezer_oauth_token_json,
    load_spotify_credentials,
    load_spotify_last_preview_at,
    load_spotify_oauth_token_json,
    load_user_profile,
    purge_expired_sessions,
    save_deezer_credentials,
    save_deezer_last_preview_at,
    save_deezer_oauth_token,
    save_spotify_credentials,
    save_spotify_last_preview_at,
    save_spotify_oauth_token,
    save_user_profile,
    user_exists,
    validate_session_token,
)
from music_review.integrations.spotify_client import SpotifyToken


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

    def test_save_credentials_clears_stored_oauth_token_json(self, db):
        create_user(db, "alice", "pw")
        token = SpotifyToken(
            access_token="a",
            token_type="Bearer",
            expires_at=datetime.now(UTC).replace(microsecond=0),
            refresh_token="r",
            scope="user-read-email",
        )
        save_spotify_oauth_token(db, "alice", spotify_token_to_json_str(token))
        assert load_spotify_oauth_token_json(db, "alice") is not None
        save_spotify_credentials(db, "alice", "cid", "csec")
        assert load_spotify_oauth_token_json(db, "alice") is None

    def test_clear_credentials_clears_oauth_token_json(self, db):
        create_user(db, "alice", "pw")
        save_spotify_credentials(db, "alice", "cid", "csec")
        token = SpotifyToken(
            access_token="a",
            token_type="Bearer",
            expires_at=datetime.now(UTC).replace(microsecond=0),
            refresh_token="r",
            scope=None,
        )
        save_spotify_oauth_token(db, "alice", spotify_token_to_json_str(token))
        clear_spotify_credentials(db, "alice")
        assert load_spotify_oauth_token_json(db, "alice") is None
        assert load_spotify_credentials(db, "alice") is None


class TestSpotifyOauthTokenJson:
    def test_save_load_roundtrip(self, db):
        create_user(db, "alice", "pw")
        token = SpotifyToken(
            access_token="acc",
            token_type="Bearer",
            expires_at=datetime(2031, 3, 1, 10, 30, 0, tzinfo=UTC),
            refresh_token="ref",
            scope="playlist-modify-private",
        )
        blob = spotify_token_to_json_str(token)
        save_spotify_oauth_token(db, "alice", blob)
        loaded = load_spotify_oauth_token_json(db, "alice")
        assert loaded == blob

    def test_clear_oauth_token(self, db):
        create_user(db, "alice", "pw")
        token = SpotifyToken(
            access_token="x",
            token_type="Bearer",
            expires_at=datetime.now(UTC).replace(microsecond=0),
            refresh_token="y",
            scope=None,
        )
        save_spotify_oauth_token(db, "alice", spotify_token_to_json_str(token))
        clear_spotify_oauth_token(db, "alice")
        assert load_spotify_oauth_token_json(db, "alice") is None

    def test_users_table_has_oauth_column_after_migration(self, db):
        create_user(db, "alice", "pw")
        cols = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        assert "spotify_oauth_token_json" in cols


class TestDeezerPreview:
    def test_save_and_load_preview_timestamp(self, db):
        create_user(db, "alice", "pw")
        save_deezer_last_preview_at(db, "alice", "2024-06-01T12:00:00Z")
        assert load_deezer_last_preview_at(db, "alice") == "2024-06-01T12:00:00Z"

    def test_load_preview_nonexistent_user(self, db):
        assert load_deezer_last_preview_at(db, "ghost") is None

    def test_load_preview_no_value_yet(self, db):
        create_user(db, "alice", "pw")
        assert load_deezer_last_preview_at(db, "alice") is None


class TestDeezerCredentials:
    def test_save_and_load_roundtrip(self, db):
        create_user(db, "alice", "pw")
        save_deezer_credentials(db, "alice", "my-app-id", "my-app-secret")
        result = load_deezer_credentials(db, "alice")
        assert result == ("my-app-id", "my-app-secret")

    def test_load_returns_none_when_not_set(self, db):
        create_user(db, "alice", "pw")
        assert load_deezer_credentials(db, "alice") is None

    def test_load_returns_none_for_nonexistent_user(self, db):
        assert load_deezer_credentials(db, "ghost") is None

    def test_clear_removes_credentials(self, db):
        create_user(db, "alice", "pw")
        save_deezer_credentials(db, "alice", "aid", "asec")
        clear_deezer_credentials(db, "alice")
        assert load_deezer_credentials(db, "alice") is None

    def test_save_trims_whitespace(self, db):
        create_user(db, "alice", "pw")
        save_deezer_credentials(db, "alice", "  aid  ", "  asec  ")
        result = load_deezer_credentials(db, "alice")
        assert result == ("aid", "asec")

    def test_overwrite_existing_credentials(self, db):
        create_user(db, "alice", "pw")
        save_deezer_credentials(db, "alice", "old-id", "old-secret")
        save_deezer_credentials(db, "alice", "new-id", "new-secret")
        result = load_deezer_credentials(db, "alice")
        assert result == ("new-id", "new-secret")

    def test_load_returns_none_when_only_app_id_set(self, db):
        create_user(db, "alice", "pw")
        db.execute(
            "UPDATE users SET deezer_app_id = ? WHERE slug = ?",
            ("aid", "alice"),
        )
        db.commit()
        assert load_deezer_credentials(db, "alice") is None

    def test_save_credentials_clears_stored_oauth_token_json(self, db):
        create_user(db, "alice", "pw")
        save_deezer_oauth_token(db, "alice", '{"access_token":"x","expires_in":0}')
        assert load_deezer_oauth_token_json(db, "alice") is not None
        save_deezer_credentials(db, "alice", "aid", "asec")
        assert load_deezer_oauth_token_json(db, "alice") is None

    def test_clear_credentials_clears_oauth_token_json(self, db):
        create_user(db, "alice", "pw")
        save_deezer_credentials(db, "alice", "aid", "asec")
        save_deezer_oauth_token(db, "alice", '{"access_token":"y","expires_in":0}')
        clear_deezer_credentials(db, "alice")
        assert load_deezer_oauth_token_json(db, "alice") is None
        assert load_deezer_credentials(db, "alice") is None


class TestDeezerOauthTokenJson:
    def test_save_load_roundtrip(self, db):
        create_user(db, "alice", "pw")
        blob = '{"access_token":"acc","expires_in":0}'
        save_deezer_oauth_token(db, "alice", blob)
        loaded = load_deezer_oauth_token_json(db, "alice")
        assert loaded == blob

    def test_clear_oauth_token(self, db):
        create_user(db, "alice", "pw")
        save_deezer_oauth_token(db, "alice", '{"access_token":"x","expires_in":3600}')
        clear_deezer_oauth_token(db, "alice")
        assert load_deezer_oauth_token_json(db, "alice") is None

    def test_users_table_has_deezer_columns_after_migration(self, db):
        create_user(db, "alice", "pw")
        cols = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        for expected in (
            "deezer_app_id",
            "deezer_app_secret",
            "deezer_oauth_token_json",
            "deezer_last_preview_at",
        ):
            assert expected in cols


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
