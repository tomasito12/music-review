"""Tests for passwordless user profile JSON store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from music_review.dashboard.taste_setup import TASTE_WIZARD_RESET_PENDING_KEY
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    SCHEMA_VERSION,
    ProfileHydrationResult,
    apply_profile_to_session,
    build_profile_payload,
    ensure_active_profile_hydrated,
    list_profile_slugs,
    load_profile,
    normalize_profile_slug,
    save_profile,
)


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


def test_save_load_roundtrip(tmp_path: Path) -> None:
    payload = build_profile_payload(
        profile_slug="test-user",
        flow_mode="combined",
        selected_communities={"1", "2", "3"},
        filter_settings={"year_min": 1990},
        community_weights_raw={"1": 0.5, "2": 1.0},
    )
    save_profile(tmp_path, "test-user", payload)
    path = tmp_path / "test-user.json"
    assert path.is_file()
    loaded = load_profile(tmp_path, "test-user")
    assert loaded is not None
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["profile_name"] == "test-user"
    assert set(loaded["selected_communities"]) == {"1", "2", "3"}
    assert loaded["filter_settings"]["year_min"] == 1990
    assert loaded["community_weights_raw"]["1"] == 0.5


def test_load_profile_missing_returns_none(tmp_path: Path) -> None:
    assert load_profile(tmp_path, "nobody") is None


def test_load_profile_invalid_json_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_profile(tmp_path, "bad") is None


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


def test_ensure_active_profile_hydrated_no_slug() -> None:
    session: dict[str, object] = {}
    assert (
        ensure_active_profile_hydrated(session, profiles_dir=Path("/nope"))
        == ProfileHydrationResult.NO_ACTIVE_SLUG
    )


def test_ensure_active_profile_hydrated_loads_from_disk(tmp_path: Path) -> None:
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
    save_profile(tmp_path, "ada", payload)
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "ada"}
    assert ensure_active_profile_hydrated(session, profiles_dir=tmp_path) == (
        ProfileHydrationResult.HYDRATED
    )
    assert session[ACTIVE_PROFILE_SESSION_KEY] == "ada"
    assert session["selected_communities"] == {"7", "8"}
    assert session["filter_settings"]["year_min"] == 2000
    assert session["community_weights_raw"] == {"7": 0.25}
    assert TASTE_WIZARD_RESET_PENDING_KEY not in session


def test_ensure_active_profile_hydrated_missing_file_clears_slug(
    tmp_path: Path,
) -> None:
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "ghost"}
    assert ensure_active_profile_hydrated(session, profiles_dir=tmp_path) == (
        ProfileHydrationResult.CLEARED_MISSING_PROFILE_FILE
    )
    assert ACTIVE_PROFILE_SESSION_KEY not in session


def test_ensure_active_profile_hydrated_invalid_slug_clears_key() -> None:
    session: dict[str, object] = {ACTIVE_PROFILE_SESSION_KEY: "!!!"}
    assert ensure_active_profile_hydrated(session, profiles_dir=Path("/nope")) == (
        ProfileHydrationResult.CLEARED_INVALID_SLUG
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


def test_list_profile_slugs_empty_dir(tmp_path: Path) -> None:
    assert list_profile_slugs(tmp_path) == []


def test_list_profile_slugs_nonexistent_dir(tmp_path: Path) -> None:
    assert list_profile_slugs(tmp_path / "does_not_exist") == []


def test_list_profile_slugs_returns_sorted_stems(tmp_path: Path) -> None:
    (tmp_path / "bob.json").write_text("{}", encoding="utf-8")
    (tmp_path / "anna.json").write_text("{}", encoding="utf-8")
    (tmp_path / "readme.txt").write_text("ignore", encoding="utf-8")
    assert list_profile_slugs(tmp_path) == ["anna", "bob"]


def test_save_atomic_replace(tmp_path: Path) -> None:
    path = tmp_path / "u.json"
    path.write_text('{"schema_version": 1}', encoding="utf-8")
    save_profile(
        tmp_path,
        "u",
        build_profile_payload(
            profile_slug="u",
            flow_mode=None,
            selected_communities=set(),
            filter_settings={},
            community_weights_raw={},
        ),
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert "saved_at" in data
