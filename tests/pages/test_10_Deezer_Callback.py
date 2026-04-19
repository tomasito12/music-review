"""Tests for the Deezer OAuth callback page (pages/10_Deezer_Callback.py)."""

from __future__ import annotations

import importlib
import types
from datetime import UTC, datetime

import pytest

from music_review.integrations.deezer_client import DeezerToken


def _deezer_callback_module() -> types.ModuleType:
    return importlib.import_module("pages.10_Deezer_Callback")


def test_deezer_callback_page_importable() -> None:
    module = _deezer_callback_module()
    assert hasattr(module, "main")


def test_deezer_authorization_code_digest_is_stable_and_length() -> None:
    module = _deezer_callback_module()
    d1 = module._deezer_authorization_code_digest("same-code")
    d2 = module._deezer_authorization_code_digest("same-code")
    assert d1 == d2
    assert len(d1) == 24


def test_deezer_oauth_spent_digests_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _deezer_callback_module()
    monkeypatch.setattr(module.st, "session_state", {})
    module._deezer_oauth_mark_code_digest_spent("digest_a")
    module._deezer_oauth_mark_code_digest_spent("digest_b")
    assert module._deezer_oauth_spent_digests_list() == ["digest_a", "digest_b"]


def test_split_deezer_oauth_callback_state_legacy_token() -> None:
    module = _deezer_callback_module()
    split = module._split_deezer_oauth_callback_state
    assert split("aB3-xY9_token_only") == ("aB3-xY9_token_only", None)


def test_split_deezer_oauth_callback_state_embeds_profile_slug() -> None:
    module = _deezer_callback_module()
    split = module._split_deezer_oauth_callback_state
    assert split("csrfpart.my-user_slug") == ("csrfpart", "my-user_slug")


def test_split_deezer_oauth_callback_state_invalid_slug_suffix_is_legacy() -> None:
    module = _deezer_callback_module()
    split = module._split_deezer_oauth_callback_state
    raw = "csrfpart.!!!"
    assert split(raw) == (raw, None)


def test_query_param_single_normalizes_list_and_str() -> None:
    module = _deezer_callback_module()
    assert module._query_param_single(None) is None
    assert module._query_param_single([]) is None
    assert module._query_param_single(["abc", "def"]) == "abc"
    assert module._query_param_single("abc") == "abc"


def test_resolve_post_oauth_target_page_streaming_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module,
        "peek_deezer_oauth_return_page_cookie",
        lambda: module.DEEZER_OAUTH_RETURN_PAGE_STREAMING_CONNECTIONS,
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_return_page_cookie", lambda: None)
    target = module._resolve_post_oauth_target_page()
    assert target.endswith("3_Streaming_Verbindungen.py")


def test_resolve_post_oauth_target_page_playlist_hub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module,
        "peek_deezer_oauth_return_page_cookie",
        lambda: module.DEEZER_OAUTH_RETURN_PAGE_PLAYLIST_HUB,
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_return_page_cookie", lambda: None)
    target = module._resolve_post_oauth_target_page()
    assert target.endswith("Spotify_Playlists.py") or target.endswith(
        "Playlist_Erzeugen.py"
    )


def test_resolve_post_oauth_target_page_default_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _deezer_callback_module()
    monkeypatch.setattr(module, "peek_deezer_oauth_return_page_cookie", lambda: None)
    monkeypatch.setattr(module, "clear_deezer_oauth_return_page_cookie", lambda: None)
    target = module._resolve_post_oauth_target_page()
    assert target.endswith("3_Streaming_Verbindungen.py")


def test_handle_oauth_callback_without_params_renders_idle_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the page is opened without ?code, show the idle hint."""
    module = _deezer_callback_module()
    monkeypatch.setattr(module.st, "query_params", {})
    rendered: list[str] = []
    monkeypatch.setattr(
        module,
        "_render_idle_callback_message",
        lambda: rendered.append("idle"),
    )

    module._handle_oauth_callback(client=None)
    assert rendered == ["idle"]


def test_handle_oauth_callback_error_param_shows_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"error_reason": "user_denied"},
    )
    errors: list[str] = []
    monkeypatch.setattr(module.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)

    module._handle_oauth_callback(client=None)
    assert errors and "user_denied" in errors[0]


def test_handle_oauth_callback_csrf_mismatch_shows_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a matching CSRF, the callback aborts with an error."""
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "the-code", "state": "csrf-from-deezer.alice"},
    )
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "_restore_profile_from_oauth_callback_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        module,
        "_maybe_restore_deezer_oauth_session_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "hydrate_deezer_token_from_db_for_active_user",
        lambda: False,
    )
    monkeypatch.setattr(module, "read_deezer_token_from_session", lambda: None)
    monkeypatch.setattr(
        module,
        "_expected_csrf_from_session_or_cookie",
        lambda: "totally-different",
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)
    errors: list[str] = []
    monkeypatch.setattr(module.st, "error", lambda msg: errors.append(msg))

    module._handle_oauth_callback(client=None)
    assert errors and "Sicherheits" in errors[0]


def test_handle_oauth_callback_success_persists_token_and_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid callback exchanges the code, persists the token, and redirects."""
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "the-code", "state": "csrf-ok"},
    )
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "_restore_profile_from_oauth_callback_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        module,
        "_maybe_restore_deezer_oauth_session_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "hydrate_deezer_token_from_db_for_active_user",
        lambda: False,
    )
    monkeypatch.setattr(module, "read_deezer_token_from_session", lambda: None)
    monkeypatch.setattr(
        module,
        "_expected_csrf_from_session_or_cookie",
        lambda: "csrf-ok",
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)
    monkeypatch.setattr(module, "clear_deezer_session_snapshot_cookie", lambda: None)

    persisted_tokens: list[DeezerToken] = []
    monkeypatch.setattr(
        module,
        "persist_deezer_token",
        lambda token: persisted_tokens.append(token),
    )

    redirected_to: list[str] = []
    monkeypatch.setattr(
        module.st,
        "switch_page",
        lambda path: redirected_to.append(path),
    )
    monkeypatch.setattr(
        module,
        "_resolve_post_oauth_target_page",
        lambda: "pages/3_Streaming_Verbindungen.py",
    )

    monkeypatch.setattr(
        module.st,
        "spinner",
        lambda *a, **k: _DummyContext(),
    )
    monkeypatch.setattr(module.st, "success", lambda msg: None)

    fake_token = DeezerToken(
        access_token="abc",
        expires_in=0,
        obtained_at=datetime.now(tz=UTC),
    )

    class _FakeClient:
        def exchange_code_for_token(self, *, code: str) -> DeezerToken:
            assert code == "the-code"
            return fake_token

    module._handle_oauth_callback(client=_FakeClient())  # type: ignore[arg-type]
    assert persisted_tokens == [fake_token]
    assert redirected_to == ["pages/3_Streaming_Verbindungen.py"]


def test_handle_oauth_callback_token_already_present_redirects_without_exchange(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a token already exists, no exchange runs and the user is redirected."""
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "the-code", "state": "csrf-ok"},
    )
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "_restore_profile_from_oauth_callback_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        module,
        "_maybe_restore_deezer_oauth_session_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "hydrate_deezer_token_from_db_for_active_user",
        lambda: True,
    )
    monkeypatch.setattr(module, "read_deezer_token_from_session", lambda: object())
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)
    monkeypatch.setattr(module, "clear_deezer_session_snapshot_cookie", lambda: None)
    monkeypatch.setattr(
        module,
        "_resolve_post_oauth_target_page",
        lambda: "pages/3_Streaming_Verbindungen.py",
    )
    redirected_to: list[str] = []
    monkeypatch.setattr(
        module.st,
        "switch_page",
        lambda path: redirected_to.append(path),
    )

    class _FakeClient:
        def exchange_code_for_token(self, *, code: str) -> DeezerToken:
            raise AssertionError("Token exchange must not run when token exists")

    module._handle_oauth_callback(client=_FakeClient())  # type: ignore[arg-type]
    assert redirected_to == ["pages/3_Streaming_Verbindungen.py"]


def test_handle_oauth_callback_failed_exchange_shows_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed token exchange surfaces a German error to the user."""
    module = _deezer_callback_module()
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "the-code", "state": "csrf-ok"},
    )
    monkeypatch.setattr(module.st, "session_state", {})
    monkeypatch.setattr(
        module,
        "_restore_profile_from_oauth_callback_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        module,
        "_maybe_restore_deezer_oauth_session_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "hydrate_deezer_token_from_db_for_active_user",
        lambda: False,
    )
    monkeypatch.setattr(module, "read_deezer_token_from_session", lambda: None)
    monkeypatch.setattr(
        module,
        "_expected_csrf_from_session_or_cookie",
        lambda: "csrf-ok",
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)
    monkeypatch.setattr(
        module.st,
        "spinner",
        lambda *a, **k: _DummyContext(),
    )
    errors: list[str] = []
    monkeypatch.setattr(module.st, "error", lambda msg: errors.append(msg))

    class _FailingClient:
        def exchange_code_for_token(self, *, code: str) -> DeezerToken:
            raise RuntimeError("Deezer API: server boom")

    module._handle_oauth_callback(client=_FailingClient())  # type: ignore[arg-type]
    assert errors and "konnte nicht abgerufen" in errors[0]


def test_handle_oauth_callback_wrong_code_uses_warning_and_marks_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deezer ``wrong code`` errors must surface as a warning, not an error."""
    module = _deezer_callback_module()
    session: dict[str, object] = {}
    monkeypatch.setattr(
        module.st,
        "query_params",
        {"code": "the-code", "state": "csrf-ok"},
    )
    monkeypatch.setattr(module.st, "session_state", session)
    monkeypatch.setattr(
        module,
        "_restore_profile_from_oauth_callback_slug",
        lambda slug: None,
    )
    monkeypatch.setattr(
        module,
        "_maybe_restore_deezer_oauth_session_snapshot",
        lambda: None,
    )
    monkeypatch.setattr(
        module,
        "hydrate_deezer_token_from_db_for_active_user",
        lambda: False,
    )
    monkeypatch.setattr(module, "read_deezer_token_from_session", lambda: None)
    monkeypatch.setattr(
        module,
        "_expected_csrf_from_session_or_cookie",
        lambda: "csrf-ok",
    )
    monkeypatch.setattr(module, "clear_deezer_oauth_state_cookie", lambda: None)
    monkeypatch.setattr(
        module.st,
        "spinner",
        lambda *a, **k: _DummyContext(),
    )
    warnings: list[str] = []
    monkeypatch.setattr(module.st, "warning", lambda msg: warnings.append(msg))

    class _ExpiredCodeClient:
        def exchange_code_for_token(self, *, code: str) -> DeezerToken:
            raise RuntimeError("Deezer: Authorization Code wrong code")

    module._handle_oauth_callback(client=_ExpiredCodeClient())  # type: ignore[arg-type]
    assert warnings and "Anmeldecode" in warnings[0]
    digest = module._deezer_authorization_code_digest("the-code")
    assert digest in module._deezer_oauth_spent_digests_list()


class _DummyContext:
    def __enter__(self) -> _DummyContext:
        return self

    def __exit__(self, *args: object) -> None:
        return None
