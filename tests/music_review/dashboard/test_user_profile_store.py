"""Tests for user profile store (SQLite-backed)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from music_review.dashboard.taste_setup import TASTE_WIZARD_RESET_PENDING_KEY
from music_review.dashboard.user_db import create_user, get_connection
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    LOGIN_GUEST_SESSION_PINNED_KEY,
    LOGIN_PROFILE_MERGE_PENDING_KEY,
    SCHEMA_VERSION,
    ProfileHydrationResult,
    apply_profile_to_session,
    build_profile_payload,
    ensure_active_profile_hydrated,
    get_spotify_preview_last_generated_at,
    load_profile,
    normalize_profile_slug,
    parse_iso_datetime_utc,
    post_login_maybe_defer_profile_apply,
    profile_document_implies_taste_complete,
    profile_taste_from_account_applied_to_session,
    record_spotify_preview_generated,
    save_profile,
    spotify_preview_cooldown_seconds_remaining,
)


@pytest.fixture(autouse=True)
def _use_test_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect DB connections to a per-test temp database."""
    db_path = tmp_path / "test_store.db"
    conn = get_connection(db_path)
    monkeypatch.setattr(
        "music_review.dashboard.user_profile_store.get_connection",
        lambda: conn,
    )
    monkeypatch.setattr(
        "music_review.dashboard.user_profile_store._db_conn",
        lambda: conn,
    )
    yield conn


def _register(conn, slug: str) -> None:
    """Shortcut to register a user for profile store tests."""
    create_user(conn, slug, "testpw")


def test_normalize_profile_slug_trims_and_lowercase() -> None:
    assert normalize_profile_slug("  Anna  ") == "anna"
    assert normalize_profile_slug("my-setup") == "my-setup"


def test_normalize_profile_slug_rejects_internal_whitespace() -> None:
    with pytest.raises(ValueError, match="Leerzeichen"):
        normalize_profile_slug("My Setup")
    with pytest.raises(ValueError, match="Leerzeichen"):
        normalize_profile_slug("tho Mas")
    with pytest.raises(ValueError, match="Leerzeichen"):
        normalize_profile_slug("a\tb")


def test_normalize_profile_slug_rejects_empty() -> None:
    with pytest.raises(ValueError, match="leer"):
        normalize_profile_slug("")
    with pytest.raises(ValueError, match="leer"):
        normalize_profile_slug("   --  ")


def test_normalize_profile_slug_rejects_too_long() -> None:
    long_name = "a" * 49
    with pytest.raises(ValueError, match="maximal"):
        normalize_profile_slug(long_name)


def test_save_load_roundtrip(_use_test_db) -> None:
    conn = _use_test_db
    _register(conn, "test-user")
    payload = build_profile_payload(
        profile_slug="test-user",
        flow_mode="combined",
        selected_communities={"1", "2", "3"},
        filter_settings={"year_min": 1990},
        community_weights_raw={"1": 0.5, "2": 1.0},
    )
    save_profile(None, "test-user", payload)
    loaded = load_profile(None, "test-user")
    assert loaded is not None
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["profile_name"] == "test-user"
    assert set(loaded["selected_communities"]) == {"1", "2", "3"}
    assert loaded["filter_settings"]["year_min"] == 1990
    assert loaded["community_weights_raw"]["1"] == 0.5


def test_load_profile_missing_returns_none(_use_test_db) -> None:
    assert load_profile(None, "nobody") is None


def test_apply_profile_to_session_with_selected_communities() -> None:
    session: dict[str, object] = {}
    fs = {
        "sort_mode": "Deterministisch",
        "year_min": 1990,
        "year_max": 2024,
        "rating_min": 7,
        "rating_max": 10,
    }
    apply_profile_to_session(
        session,
        {
            "selected_communities": ["10", "20", "30"],
            "filter_settings": fs,
            "community_weights_raw": {"10": 1.0},
            "flow_mode": "artists",
        },
    )
    assert session["selected_communities"] == {"10", "20", "30"}
    assert session["filter_settings"] == fs
    assert session["community_weights_raw"] == {"10": 1.0}
    assert session["flow_mode"] == "artists"
    assert TASTE_WIZARD_RESET_PENDING_KEY not in session


def test_profile_taste_from_account_applied_to_session_false_without_slug() -> None:
    assert not profile_taste_from_account_applied_to_session({})


def test_profile_taste_from_account_applied_to_session_false_when_merge_pending() -> (
    None
):
    session: dict[str, object] = {
        ACTIVE_PROFILE_SESSION_KEY: "ada",
        LOGIN_PROFILE_MERGE_PENDING_KEY: {"server_profile": {}},
    }
    assert not profile_taste_from_account_applied_to_session(session)


def test_profile_taste_from_account_applied_to_session_false_when_guest_pinned() -> (
    None
):
    session: dict[str, object] = {
        ACTIVE_PROFILE_SESSION_KEY: "ada",
        LOGIN_GUEST_SESSION_PINNED_KEY: True,
    }
    assert not profile_taste_from_account_applied_to_session(session)


def test_profile_taste_from_account_applied_to_session_true_when_logged_in_clean() -> (
    None
):
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "ada"}
    assert profile_taste_from_account_applied_to_session(session)


def test_ensure_active_profile_hydrated_no_slug() -> None:
    session: dict[str, object] = {}
    assert (
        ensure_active_profile_hydrated(session) == ProfileHydrationResult.NO_ACTIVE_SLUG
    )


def test_profile_document_implies_taste_complete_false_when_empty() -> None:
    assert not profile_document_implies_taste_complete(
        {
            "selected_communities": [],
            "filter_settings": {},
            "community_weights_raw": {},
        },
    )


def test_profile_document_implies_taste_complete_true_when_complete() -> None:
    doc = build_profile_payload(
        profile_slug="x",
        flow_mode="combined",
        selected_communities={"42"},
        filter_settings={
            "year_min": 1990,
            "year_max": 2024,
            "rating_min": 0,
            "rating_max": 10,
        },
        community_weights_raw={"42": 1.0},
    )
    assert profile_document_implies_taste_complete(doc)


def test_post_login_defer_profile_apply_sets_merge_pending(_use_test_db) -> None:
    conn = _use_test_db
    _register(conn, "defer-user")
    payload = build_profile_payload(
        profile_slug="defer-user",
        flow_mode="combined",
        selected_communities={"9"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"9": 1.0},
    )
    save_profile(None, "defer-user", payload)
    session: dict[str, object] = {
        "selected_communities": {"1"},
        "artist_flow_selected_communities": {"1"},
        "genre_flow_selected_communities": set(),
        "filter_settings": {},
        "community_weights_raw": {},
    }
    assert post_login_maybe_defer_profile_apply(
        session,
        profile_slug="defer-user",
        server_profile=payload,
    )
    assert LOGIN_PROFILE_MERGE_PENDING_KEY in session
    assert session[ACTIVE_PROFILE_SESSION_KEY] == "defer-user"
    assert session["selected_communities"] == {"1"}


def test_post_login_applies_server_when_session_has_no_guest_prefs(
    _use_test_db,
) -> None:
    conn = _use_test_db
    _register(conn, "clean-user")
    payload = build_profile_payload(
        profile_slug="clean-user",
        flow_mode="combined",
        selected_communities={"9"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"9": 1.0},
    )
    save_profile(None, "clean-user", payload)
    session: dict[str, object] = {}
    assert not post_login_maybe_defer_profile_apply(
        session,
        profile_slug="clean-user",
        server_profile=payload,
    )
    assert LOGIN_PROFILE_MERGE_PENDING_KEY not in session
    assert session["selected_communities"] == {"9"}


def test_ensure_active_profile_hydrated_skips_disk_when_guest_session_pinned(
    _use_test_db,
) -> None:
    conn = _use_test_db
    _register(conn, "pin-user")
    payload = build_profile_payload(
        profile_slug="pin-user",
        flow_mode="combined",
        selected_communities={"1"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"1": 1.0},
    )
    save_profile(None, "pin-user", payload)
    session: dict[str, object] = {
        ACTIVE_PROFILE_SESSION_KEY: "pin-user",
        LOGIN_GUEST_SESSION_PINNED_KEY: True,
        "selected_communities": {"88"},
        "filter_settings": {
            "year_min": 1980,
            "year_max": 2020,
            "rating_min": 1,
            "rating_max": 9,
        },
        "community_weights_raw": {"88": 0.5},
    }
    assert ensure_active_profile_hydrated(session) == ProfileHydrationResult.HYDRATED
    assert session["selected_communities"] == {"88"}


def test_ensure_active_profile_hydrated_skips_disk_when_merge_pending(
    _use_test_db,
) -> None:
    conn = _use_test_db
    _register(conn, "merge-skip")
    payload = build_profile_payload(
        profile_slug="merge-skip",
        flow_mode="combined",
        selected_communities={"1"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"1": 1.0},
    )
    save_profile(None, "merge-skip", payload)
    session: dict[str, object] = {
        ACTIVE_PROFILE_SESSION_KEY: "merge-skip",
        LOGIN_PROFILE_MERGE_PENDING_KEY: {"server_profile": dict(payload)},
        "selected_communities": {"9"},
        "filter_settings": {
            "year_min": 1980,
            "year_max": 2020,
            "rating_min": 1,
            "rating_max": 9,
        },
        "community_weights_raw": {"9": 0.5},
    }
    assert ensure_active_profile_hydrated(session) == ProfileHydrationResult.HYDRATED
    assert session["selected_communities"] == {"9"}
    assert session["filter_settings"]["year_min"] == 1980


def test_ensure_active_profile_hydrated_skips_disk_when_reset_pending(
    _use_test_db,
) -> None:
    conn = _use_test_db
    _register(conn, "bob")
    payload = build_profile_payload(
        profile_slug="bob",
        flow_mode="combined",
        selected_communities={"99"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"99": 1.0},
    )
    save_profile(None, "bob", payload)
    session: dict[str, object] = {
        ACTIVE_PROFILE_SESSION_KEY: "bob",
        TASTE_WIZARD_RESET_PENDING_KEY: True,
        "selected_communities": set(),
        "filter_settings": {},
        "community_weights_raw": {},
    }
    assert ensure_active_profile_hydrated(session) == ProfileHydrationResult.HYDRATED
    assert session["selected_communities"] == set()
    assert session["filter_settings"] == {}
    assert session["community_weights_raw"] == {}
    assert session.get(TASTE_WIZARD_RESET_PENDING_KEY) is True


def test_ensure_active_profile_hydrated_loads_from_db(_use_test_db) -> None:
    conn = _use_test_db
    _register(conn, "ada")
    payload = build_profile_payload(
        profile_slug="ada",
        flow_mode="combined",
        selected_communities={"7", "8"},
        filter_settings={
            "year_min": 2000,
            "year_max": 2024,
            "rating_min": 7,
            "rating_max": 10,
        },
        community_weights_raw={"7": 0.25},
    )
    save_profile(None, "ada", payload)
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "ada"}
    assert ensure_active_profile_hydrated(session) == ProfileHydrationResult.HYDRATED
    assert session[ACTIVE_PROFILE_SESSION_KEY] == "ada"
    assert session["selected_communities"] == {"7", "8"}
    assert session["filter_settings"]["year_min"] == 2000
    assert session["community_weights_raw"] == {"7": 0.25}
    assert TASTE_WIZARD_RESET_PENDING_KEY not in session


def test_ensure_active_profile_hydrated_missing_user_clears_slug(
    _use_test_db,
) -> None:
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "ghost"}
    assert (
        ensure_active_profile_hydrated(session)
        == ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE
    )
    assert ACTIVE_PROFILE_SESSION_KEY not in session


def test_ensure_active_profile_hydrated_invalid_slug_clears_key() -> None:
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "!!!"}
    assert (
        ensure_active_profile_hydrated(session)
        == ProfileHydrationResult.CLEARED_INVALID_SLUG
    )
    assert ACTIVE_PROFILE_SESSION_KEY not in session


def test_apply_profile_to_session_legacy_fallback() -> None:
    session: dict[str, object] = {}
    apply_profile_to_session(
        session,
        {
            "artist_flow_selected_communities": ["10", "20"],
            "genre_flow_selected_communities": ["30"],
            "filter_settings": {},
            "flow_mode": None,
        },
    )
    assert session["selected_communities"] == {"10", "20", "30"}
    assert session["artist_flow_selected_communities"] == {"10", "20", "30"}
    assert session.get(TASTE_WIZARD_RESET_PENDING_KEY) is True


def test_parse_iso_datetime_utc_accepts_z_suffix() -> None:
    dt = parse_iso_datetime_utc("2024-01-15T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.year == 2024


def test_spotify_preview_cooldown_zero_when_never_generated() -> None:
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert (
        spotify_preview_cooldown_seconds_remaining(
            now_utc=now,
            last_generated_at_utc=None,
        )
        == 0
    )


def test_spotify_preview_cooldown_full_window_right_after_generation() -> None:
    now = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    last = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    rem = spotify_preview_cooldown_seconds_remaining(
        now_utc=now,
        last_generated_at_utc=last,
        cooldown_seconds=600,
    )
    assert rem == 600


def test_spotify_preview_cooldown_expired_after_interval() -> None:
    now = datetime(2024, 6, 1, 13, 0, 0, tzinfo=UTC)
    last = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert (
        spotify_preview_cooldown_seconds_remaining(
            now_utc=now,
            last_generated_at_utc=last,
            cooldown_seconds=600,
        )
        == 0
    )


def test_record_spotify_preview_guest_writes_session_only(
    _use_test_db,
) -> None:
    session: dict[str, object] = {}
    when = datetime(2024, 3, 1, 10, 30, 0, tzinfo=UTC)
    record_spotify_preview_generated(
        session=session,
        profiles_dir=Path("/unused"),
        when_utc=when,
    )
    assert isinstance(session.get("spotify_last_preview_generated_at"), str)


def test_record_and_get_spotify_preview_with_db_user(_use_test_db) -> None:
    conn = _use_test_db
    _register(conn, "u1")
    payload = build_profile_payload(
        profile_slug="u1",
        flow_mode="combined",
        selected_communities={"1"},
        filter_settings={},
        community_weights_raw={},
    )
    save_profile(None, "u1", payload)
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "u1"}
    when = datetime(2024, 5, 1, 8, 0, 0, tzinfo=UTC)
    record_spotify_preview_generated(
        session=session,
        profiles_dir=Path("/unused"),
        when_utc=when,
    )
    got = get_spotify_preview_last_generated_at(
        session=session,
        profiles_dir=Path("/unused"),
    )
    assert got is not None
    assert (
        spotify_preview_cooldown_seconds_remaining(
            now_utc=when,
            last_generated_at_utc=got,
            cooldown_seconds=600,
        )
        == 600
    )
