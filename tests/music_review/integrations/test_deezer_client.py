"""Tests for the Deezer REST API client wrapper."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_review.integrations.deezer_client import (
    DEEZER_API_BASE_URL,
    DEEZER_AUTH_BASE_URL,
    DeezerAuthConfig,
    DeezerClient,
    DeezerConfigError,
    DeezerToken,
    deezer_track_id_from_uri,
    deezer_track_uri,
    normalize_streamlit_deezer_redirect_uri,
    resolve_deezer_redirect_uri,
)


def _sample_token_body_no_expiry() -> str:
    return "access_token=acc123&expires=0"


def _sample_token_body_short_lived() -> str:
    return "access_token=acc456&expires=3600"


def test_deezer_auth_config_from_env_missing_app_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("DEEZER_APP_ID", raising=False)
    monkeypatch.delenv("DEEZER_APP_SECRET", raising=False)
    monkeypatch.delenv("DEEZER_REDIRECT_URI", raising=False)
    monkeypatch.delenv("DEEZER_PERMS", raising=False)
    (tmp_path / ".env").write_text("# empty for test\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(DeezerConfigError):
        DeezerAuthConfig.from_env()


def test_deezer_auth_config_from_env_loads_full_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEZER_APP_ID", "1234")
    monkeypatch.setenv("DEEZER_APP_SECRET", "topsecret")
    monkeypatch.setenv("DEEZER_REDIRECT_URI", "http://localhost:8501/deezer_callback")
    monkeypatch.delenv("DEEZER_PERMS", raising=False)
    cfg = DeezerAuthConfig.from_env()
    assert cfg.app_id == "1234"
    assert cfg.app_secret == "topsecret"
    assert cfg.redirect_uri == "http://localhost:8501/deezer_callback"
    assert "manage_library" in cfg.perms
    assert "offline_access" in cfg.perms


def test_deezer_auth_config_from_env_normalizes_callback_path_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEZER_APP_ID", "1")
    monkeypatch.setenv("DEEZER_APP_SECRET", "s")
    monkeypatch.setenv(
        "DEEZER_REDIRECT_URI",
        "http://127.0.0.1:8501/Deezer_Callback",
    )
    cfg = DeezerAuthConfig.from_env()
    assert cfg.redirect_uri == "http://127.0.0.1:8501/deezer_callback"


def test_deezer_auth_config_from_env_custom_perms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEZER_APP_ID", "1")
    monkeypatch.setenv("DEEZER_APP_SECRET", "s")
    monkeypatch.setenv("DEEZER_REDIRECT_URI", "http://x/deezer_callback")
    monkeypatch.setenv("DEEZER_PERMS", "basic_access,email")
    cfg = DeezerAuthConfig.from_env()
    assert cfg.perms == ("basic_access", "email")


class TestFromUserCredentials:
    def test_builds_config_with_explicit_redirect(self) -> None:
        cfg = DeezerAuthConfig.from_user_credentials(
            app_id="aid",
            app_secret="asec",
            redirect_uri="http://127.0.0.1:8501/deezer_callback",
        )
        assert cfg.app_id == "aid"
        assert cfg.app_secret == "asec"
        assert cfg.redirect_uri == "http://127.0.0.1:8501/deezer_callback"
        assert "manage_library" in cfg.perms
        assert "offline_access" in cfg.perms

    def test_falls_back_to_env_redirect_uri(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "DEEZER_REDIRECT_URI",
            "http://example.com/deezer_callback",
        )
        cfg = DeezerAuthConfig.from_user_credentials(
            app_id="aid",
            app_secret="asec",
        )
        assert cfg.redirect_uri == "http://example.com/deezer_callback"

    def test_raises_when_empty_app_id(self) -> None:
        with pytest.raises(DeezerConfigError):
            DeezerAuthConfig.from_user_credentials(
                app_id="",
                app_secret="s",
                redirect_uri="http://x/cb",
            )

    def test_raises_when_empty_app_secret(self) -> None:
        with pytest.raises(DeezerConfigError):
            DeezerAuthConfig.from_user_credentials(
                app_id="aid",
                app_secret="",
                redirect_uri="http://x/cb",
            )

    def test_raises_when_no_redirect_uri_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DEEZER_REDIRECT_URI", raising=False)
        with pytest.raises(DeezerConfigError):
            DeezerAuthConfig.from_user_credentials(
                app_id="aid",
                app_secret="asec",
            )

    def test_normalizes_redirect_uri_casing(self) -> None:
        cfg = DeezerAuthConfig.from_user_credentials(
            app_id="aid",
            app_secret="asec",
            redirect_uri="http://host/Deezer_Callback",
        )
        assert cfg.redirect_uri == "http://host/deezer_callback"

    def test_custom_perms(self) -> None:
        cfg = DeezerAuthConfig.from_user_credentials(
            app_id="aid",
            app_secret="asec",
            redirect_uri="http://x/cb",
            perms=("basic_access",),
        )
        assert cfg.perms == ("basic_access",)


def test_normalize_streamlit_deezer_redirect_uri_fixes_case() -> None:
    assert (
        normalize_streamlit_deezer_redirect_uri(
            "http://127.0.0.1:8501/Deezer_Callback",
        )
        == "http://127.0.0.1:8501/deezer_callback"
    )


def test_normalize_deezer_redirect_uri_keeps_other_paths() -> None:
    uri = "http://127.0.0.1:8501/other/cb"
    assert normalize_streamlit_deezer_redirect_uri(uri) == uri


def test_normalize_deezer_redirect_uri_empty_input() -> None:
    assert normalize_streamlit_deezer_redirect_uri("   ") == ""


def test_resolve_deezer_redirect_uri_uses_configured_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEZER_OAUTH_USE_BROWSER_REDIRECT_URI", raising=False)
    assert (
        resolve_deezer_redirect_uri(
            configured="http://127.0.0.1:8501/cb",
            browser_url="http://localhost:8501/deezer_callback",
        )
        == "http://127.0.0.1:8501/cb"
    )


def test_resolve_deezer_redirect_uri_uses_browser_when_env_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEZER_OAUTH_USE_BROWSER_REDIRECT_URI", "1")
    assert (
        resolve_deezer_redirect_uri(
            configured="http://127.0.0.1:8501/cb",
            browser_url="http://localhost:8501/deezer_callback",
        )
        == "http://localhost:8501/deezer_callback"
    )


def test_deezer_token_parses_form_encoded_body_no_expiry() -> None:
    token = DeezerToken.from_token_response_text(_sample_token_body_no_expiry())
    assert token.access_token == "acc123"
    assert token.expires_in == 0
    assert token.is_expired() is False


def test_deezer_token_parses_form_encoded_body_short_lived() -> None:
    token = DeezerToken.from_token_response_text(_sample_token_body_short_lived())
    assert token.access_token == "acc456"
    assert token.expires_in == 3600
    assert token.is_expired() is False


def test_deezer_token_is_expired_with_leeway() -> None:
    obtained = datetime.now(tz=UTC) - timedelta(seconds=3590)
    token = DeezerToken(
        access_token="x",
        expires_in=3600,
        obtained_at=obtained,
    )
    assert token.is_expired(leeway_seconds=60) is True
    assert token.is_expired(leeway_seconds=1) is False


def test_deezer_token_offline_token_never_expires() -> None:
    """Tokens issued with ``offline_access`` always report ``is_expired==False``."""
    token = DeezerToken(
        access_token="x",
        expires_in=0,
        obtained_at=datetime(1990, 1, 1, tzinfo=UTC),
    )
    assert token.is_expired() is False


def test_deezer_token_raises_for_empty_response() -> None:
    with pytest.raises(ValueError, match="Empty"):
        DeezerToken.from_token_response_text("")


def test_deezer_token_raises_for_missing_access_token() -> None:
    with pytest.raises(ValueError, match="missing"):
        DeezerToken.from_token_response_text("expires=0")


def test_deezer_token_raises_for_wrong_code_message() -> None:
    with pytest.raises(ValueError, match="wrong"):
        DeezerToken.from_token_response_text("wrong code, please send a valid code")


def test_deezer_track_uri_helpers_roundtrip() -> None:
    assert deezer_track_uri("12345") == "deezer:track:12345"
    assert deezer_track_id_from_uri("deezer:track:12345") == "12345"
    assert deezer_track_id_from_uri("spotify:track:abc") is None
    assert deezer_track_id_from_uri("") is None


def test_build_authorize_url_contains_expected_query() -> None:
    cfg = DeezerAuthConfig(
        app_id="aid",
        app_secret="asec",
        redirect_uri="http://localhost/deezer_callback",
        perms=("manage_library", "offline_access"),
    )
    client = DeezerClient(cfg)
    url = client.build_authorize_url(state="xyz")
    assert url.startswith(f"{DEEZER_AUTH_BASE_URL}/auth.php?")
    assert "app_id=aid" in url
    assert "state=xyz" in url
    assert "perms=manage_library%2Coffline_access" in url


def test_with_redirect_uri_returns_independent_client() -> None:
    base = DeezerClient(
        DeezerAuthConfig(
            app_id="aid",
            app_secret="asec",
            redirect_uri="http://old/cb",
            perms=("manage_library",),
        ),
    )
    other = base.with_redirect_uri("http://new/cb")
    assert base.redirect_uri == "http://old/cb"
    assert other.redirect_uri == "http://new/cb"


def test_with_redirect_uri_rejects_empty() -> None:
    client = DeezerClient(
        DeezerAuthConfig(
            app_id="a",
            app_secret="s",
            redirect_uri="http://x/cb",
            perms=("manage_library",),
        ),
    )
    with pytest.raises(ValueError, match="redirect_uri"):
        client.with_redirect_uri("  ")


def _make_client() -> DeezerClient:
    return DeezerClient(
        DeezerAuthConfig(
            app_id="aid",
            app_secret="asec",
            redirect_uri="http://localhost/deezer_callback",
            perms=("manage_library", "offline_access"),
        ),
    )


@patch("music_review.integrations.deezer_client.requests.get")
def test_exchange_code_for_token_success_with_form_body(mock_get: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = _sample_token_body_no_expiry()
    mock_get.return_value = mock_resp

    token = client.exchange_code_for_token(code="abc")
    assert token.access_token == "acc123"
    assert token.expires_in == 0
    args, kwargs = mock_get.call_args
    assert args[0] == f"{DEEZER_AUTH_BASE_URL}/access_token.php"
    assert kwargs["params"]["app_id"] == "aid"
    assert kwargs["params"]["secret"] == "asec"
    assert kwargs["params"]["code"] == "abc"


@patch("music_review.integrations.deezer_client.requests.get")
def test_exchange_code_for_token_success_with_json_body(mock_get: MagicMock) -> None:
    """``output=json`` produces a JSON body; the parser must accept it."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"access_token":"acc789","expires":3600}'
    mock_get.return_value = mock_resp

    token = client.exchange_code_for_token(code="abc")
    assert token.access_token == "acc789"
    assert token.expires_in == 3600


@patch("music_review.integrations.deezer_client.requests.get")
def test_exchange_code_for_token_http_error_raises(mock_get: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "internal error"
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError, match="500"):
        client.exchange_code_for_token(code="abc")


@patch("music_review.integrations.deezer_client.requests.get")
def test_exchange_code_for_token_wrong_code_raises_friendly(
    mock_get: MagicMock,
) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "wrong code, please send a valid code"
    mock_get.return_value = mock_resp

    with pytest.raises(RuntimeError, match="wrong"):
        client.exchange_code_for_token(code="bogus")


def _make_token() -> DeezerToken:
    return DeezerToken(
        access_token="tok",
        expires_in=0,
        obtained_at=datetime.now(tz=UTC),
    )


@patch("music_review.integrations.deezer_client.requests.request")
def test_get_current_user_id_returns_string(mock_req: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {"id": 42, "name": "Alice"}
    mock_req.return_value = mock_resp

    uid = client.get_current_user_id(token=_make_token())
    assert uid == "42"
    _args, kwargs = mock_req.call_args
    assert kwargs["url"] == f"{DEEZER_API_BASE_URL}/user/me"
    assert kwargs["params"]["access_token"] == "tok"


@patch("music_review.integrations.deezer_client.requests.request")
def test_application_level_error_is_translated_to_runtime(mock_req: MagicMock) -> None:
    """Deezer signals errors with HTTP 200 + ``{"error":...}`` JSON body."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "error": {
            "type": "OAuthException",
            "message": "Invalid OAuth access token",
            "code": 300,
        }
    }
    mock_req.return_value = mock_resp

    with pytest.raises(RuntimeError, match="OAuthException"):
        client.get_current_user_id(token=_make_token())


@patch("music_review.integrations.deezer_client.requests.request")
def test_rate_limit_429_is_translated_to_runtime(mock_req: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.ok = False
    mock_resp.headers = {"Retry-After": "3"}
    mock_req.return_value = mock_resp

    with pytest.raises(RuntimeError, match="rate limit"):
        client.get_current_user_id(token=_make_token())


def test_build_track_search_query_combines_artist_and_title() -> None:
    q = DeezerClient.build_track_search_query(artist="Radiohead", title="Lucky")
    assert 'artist:"Radiohead"' in q
    assert 'track:"Lucky"' in q


def test_build_track_search_query_handles_quotes() -> None:
    q = DeezerClient.build_track_search_query(artist='Brand "X"', title="Song")
    assert '"' not in q.split("artist:")[1].split(" ")[0][1:-1]


def test_build_track_search_query_empty_returns_empty() -> None:
    assert DeezerClient.build_track_search_query(artist="", title="") == ""


@patch("music_review.integrations.deezer_client.requests.request")
def test_search_tracks_parses_results(mock_req: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {
        "data": [
            {
                "id": 1,
                "title": "Lucky",
                "artist": {"name": "Radiohead"},
                "album": {"title": "OK Computer"},
                "link": "https://www.deezer.com/track/1",
            },
            {"id": 2, "title": "Karma Police", "artist": {"name": "Radiohead"}},
        ]
    }
    mock_req.return_value = mock_resp

    results = client.search_tracks(query='artist:"Radiohead"', token=_make_token())
    assert len(results) == 2
    assert results[0].id == "1"
    assert results[0].title == "Lucky"
    assert results[0].artist == "Radiohead"
    assert results[0].album == "OK Computer"
    assert results[0].link == "https://www.deezer.com/track/1"
    assert results[1].album is None


@patch("music_review.integrations.deezer_client.requests.request")
def test_search_tracks_empty_query_returns_empty_without_request(
    mock_req: MagicMock,
) -> None:
    client = _make_client()
    assert client.search_tracks(query="   ", token=_make_token()) == []
    mock_req.assert_not_called()


@patch("music_review.integrations.deezer_client.requests.request")
def test_create_playlist_returns_id_and_link(mock_req: MagicMock) -> None:
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.json.return_value = {"id": 999}
    mock_req.return_value = mock_resp

    pl = client.create_playlist(title="Test PL", token=_make_token())
    assert pl.id == "999"
    assert pl.title == "Test PL"
    assert pl.link == "https://www.deezer.com/playlist/999"
    _args, kwargs = mock_req.call_args
    assert kwargs["url"] == f"{DEEZER_API_BASE_URL}/user/me/playlists"
    assert kwargs["params"]["title"] == "Test PL"


def test_create_playlist_rejects_empty_title() -> None:
    client = _make_client()
    with pytest.raises(ValueError, match="title"):
        client.create_playlist(title="   ", token=_make_token())


@patch("music_review.integrations.deezer_client.time.sleep")
@patch("music_review.integrations.deezer_client.requests.request")
def test_add_tracks_chunks_and_sends_comma_separated(
    mock_req: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = True
    mock_req.return_value = ok_resp

    track_ids = [str(i) for i in range(1, 121)]
    client.add_tracks_to_playlist(
        playlist_id="42",
        track_ids=track_ids,
        token=_make_token(),
        chunk_size=50,
    )
    assert mock_req.call_count == 3
    songs_param = mock_req.call_args_list[0].kwargs["params"]["songs"]
    assert songs_param.startswith("1,2,3,")
    assert mock_sleep.called


@patch("music_review.integrations.deezer_client.requests.request")
def test_add_tracks_noop_for_empty_list(mock_req: MagicMock) -> None:
    client = _make_client()
    client.add_tracks_to_playlist(playlist_id="x", track_ids=[], token=_make_token())
    mock_req.assert_not_called()


@patch("music_review.integrations.deezer_client.time.sleep")
@patch("music_review.integrations.deezer_client.requests.request")
def test_remove_tracks_chunks_and_uses_delete(
    mock_req: MagicMock,
    mock_sleep: MagicMock,
) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = True
    mock_req.return_value = ok_resp

    client.remove_tracks_from_playlist(
        playlist_id="42",
        track_ids=["1", "2", "3"],
        token=_make_token(),
    )
    _args, kwargs = mock_req.call_args
    assert kwargs["method"] == "DELETE"
    assert kwargs["params"]["songs"] == "1,2,3"
    mock_sleep.assert_not_called()  # Single chunk: no sleep needed.


@patch("music_review.integrations.deezer_client.requests.request")
def test_set_playlist_visibility_sends_public_param(mock_req: MagicMock) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = True
    mock_req.return_value = ok_resp

    client.set_playlist_visibility(
        playlist_id="42",
        public=True,
        token=_make_token(),
    )
    _args, kwargs = mock_req.call_args
    assert kwargs["params"]["public"] == "true"
    assert kwargs["url"].endswith("/playlist/42")


@patch("music_review.integrations.deezer_client.requests.request")
def test_set_playlist_visibility_false_sends_lowercase_string(
    mock_req: MagicMock,
) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = True
    mock_req.return_value = ok_resp

    client.set_playlist_visibility(
        playlist_id="42",
        public=False,
        token=_make_token(),
    )
    assert mock_req.call_args.kwargs["params"]["public"] == "false"


@patch("music_review.integrations.deezer_client.requests.request")
def test_find_owned_playlist_id_by_display_name_finds_match_first_page(
    mock_req: MagicMock,
) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = {
        "data": [
            {"id": 1, "title": "Other"},
            {"id": 2, "title": "My Mix"},
            {"id": 3, "title": "Workout"},
        ]
    }
    mock_req.return_value = ok_resp

    pid = client.find_owned_playlist_id_by_display_name(
        display_name="my mix",
        token=_make_token(),
    )
    assert pid == "2"


@patch("music_review.integrations.deezer_client.requests.request")
def test_find_owned_playlist_id_by_display_name_returns_none_when_no_match(
    mock_req: MagicMock,
) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = {"data": [{"id": 1, "title": "Other"}]}
    mock_req.return_value = ok_resp

    pid = client.find_owned_playlist_id_by_display_name(
        display_name="missing",
        token=_make_token(),
    )
    assert pid is None


@patch("music_review.integrations.deezer_client.requests.request")
def test_list_playlist_track_ids_returns_strings(mock_req: MagicMock) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = {
        "data": [{"id": 10}, {"id": 20}, {"id": 30}],
    }
    mock_req.return_value = ok_resp

    ids = client.list_playlist_track_ids(playlist_id="42", token=_make_token())
    assert ids == ["10", "20", "30"]


@patch("music_review.integrations.deezer_client.requests.request")
def test_get_playlist_returns_full_dataclass(mock_req: MagicMock) -> None:
    client = _make_client()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.ok = True
    ok_resp.json.return_value = {
        "id": 42,
        "title": "My Playlist",
        "link": "https://www.deezer.com/playlist/42",
    }
    mock_req.return_value = ok_resp

    pl = client.get_playlist(playlist_id="42", token=_make_token())
    assert pl.id == "42"
    assert pl.title == "My Playlist"
    assert pl.link == "https://www.deezer.com/playlist/42"
