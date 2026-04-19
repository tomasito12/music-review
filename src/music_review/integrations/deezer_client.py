"""Typed client wrapper for the Deezer REST API.

Deezer's API differs from Spotify in several user-visible ways:

* Authorization endpoint is ``https://connect.deezer.com/oauth/auth.php``
  with parameters ``app_id``, ``redirect_uri``, ``perms`` (comma separated),
  and ``state``. There is **no PKCE** flow; ``app_id`` and ``secret`` are
  always required.
* The token endpoint returns a ``application/x-www-form-urlencoded`` body
  (e.g. ``access_token=XYZ&expires=0``) instead of JSON.
* There is **no refresh token mechanism**. Requesting the ``offline_access``
  permission produces tokens with ``expires=0`` (no expiry); without it the
  user must re-authenticate.
* The REST API at ``https://api.deezer.com`` authenticates via the
  ``access_token`` query parameter, not a Bearer header.
* Public IP-based rate limit is around ``50 requests per 5 seconds``; the
  client therefore throttles bulk operations such as track search.

This client is stateless with respect to tokens; the caller is responsible
for storing :class:`DeezerToken` instances (e.g. in Streamlit session state).
"""

from __future__ import annotations

import logging
import time
import unicodedata
import urllib.parse
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from os import getcwd, getenv
from pathlib import Path
from typing import Any, Final

import requests

# Importing config triggers `.env` loading via its side effects.
from music_review import config as _config  # noqa: F401

LOGGER: Final = logging.getLogger(__name__)

DEEZER_AUTH_BASE_URL: Final = "https://connect.deezer.com/oauth"
DEEZER_API_BASE_URL: Final = "https://api.deezer.com"
# Must match ``url_path`` on the Streamlit Page for ``10_Deezer_Callback.py``.
STREAMLIT_DEEZER_PAGE_PATH: Final = "deezer_callback"

# Deezer enforces a public ``50 requests / 5 seconds`` per-IP quota. We stay
# well below that for bulk track searches by sleeping between calls.
DEEZER_BULK_REQUEST_INTERVAL_SECONDS: Final = 0.12


def normalize_streamlit_deezer_redirect_uri(redirect_uri: str) -> str:
    """Rewrite the Deezer Streamlit page path to the canonical lowercase segment.

    Streamlit serves the callback page at ``url_path="deezer_callback"``. If
    ``DEEZER_REDIRECT_URI`` uses the same segment with different casing (e.g.
    ``/Deezer_Callback``), OAuth and the browser path disagree. The last path
    segment is compared case-insensitively to :data:`STREAMLIT_DEEZER_PAGE_PATH`
    and replaced with the canonical spelling when they match.
    """
    raw = redirect_uri.strip()
    if not raw:
        return raw
    parsed = urllib.parse.urlparse(raw)
    segments = [segment for segment in (parsed.path or "").split("/") if segment]
    if not segments:
        return raw
    if segments[-1].casefold() != STREAMLIT_DEEZER_PAGE_PATH.casefold():
        return raw
    segments[-1] = STREAMLIT_DEEZER_PAGE_PATH
    new_path = "/" + "/".join(segments)
    return urllib.parse.urlunparse(parsed._replace(path=new_path))


def _deezer_token_error_message(response: requests.Response) -> str:
    """Human-readable message from a failed Deezer OAuth token endpoint response."""
    raw = (response.text or "").strip()
    status = int(response.status_code)
    if "wrong code" in raw.lower():
        return "Deezer: Authorization Code ist ungültig oder abgelaufen."
    return f"Deezer token endpoint HTTP {status}: {raw[:800]}"


def _deezer_api_error_message(response: requests.Response) -> str:
    """Build a short error string from a failed Deezer API response.

    Deezer indicates errors by returning HTTP 200 with a JSON body of the form
    ``{"error": {"type": "OAuthException", "message": "...", "code": 300}}``,
    so callers must inspect responses even when the status code is 200.
    """
    raw = (response.text or "").strip()
    status = int(response.status_code)
    try:
        parsed: Any = response.json()
    except ValueError:
        return f"Deezer API HTTP {status}: {raw[:800]}"
    if isinstance(parsed, dict):
        err = parsed.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            etype = err.get("type")
            if isinstance(msg, str) and msg.strip():
                if isinstance(etype, str) and etype.strip():
                    return f"Deezer API ({etype.strip()}): {msg.strip()}"
                return f"Deezer API: {msg.strip()}"
    return f"Deezer API HTTP {status}: {raw[:800]}"


class DeezerConfigError(RuntimeError):
    """Raised when required Deezer configuration is missing or invalid."""


def _deezer_oauth_use_browser_redirect_override() -> bool:
    """True when env ``DEEZER_OAUTH_USE_BROWSER_REDIRECT_URI`` enables browser URL."""
    raw = (getenv("DEEZER_OAUTH_USE_BROWSER_REDIRECT_URI") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_deezer_redirect_uri(
    *,
    configured: str,
    browser_url: str | None,
) -> str:
    """Return the redirect URI to send to Deezer for authorize and token exchange.

    Mirrors the Spotify variant: by default the configured value is returned
    verbatim. Set ``DEEZER_OAUTH_USE_BROWSER_REDIRECT_URI=1`` to instead send
    the live browser URL when it begins with ``http(s)://``.
    """
    if _deezer_oauth_use_browser_redirect_override() and isinstance(browser_url, str):
        candidate = browser_url.strip()
        if candidate.startswith(("http://", "https://")):
            return candidate
    return configured.strip()


def _load_dotenv_keys_if_unset(keys: Iterable[str]) -> None:
    """Populate ``os.environ`` from a local ``.env`` file for the listed keys.

    Mirrors the lightweight loader used by the Spotify config so behaviour is
    predictable even when ``python-dotenv`` is unavailable.
    """
    env_path = Path(getcwd()) / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in keys and not getenv(key):
                import os

                os.environ[key] = value
    except Exception:
        # The fallback loader must not break the caller.
        pass


@dataclass(slots=True)
class DeezerAuthConfig:
    """Static configuration for Deezer OAuth.

    Instances are usually created via :meth:`DeezerAuthConfig.from_env` (shared
    project app from ``.env``) or :meth:`DeezerAuthConfig.from_user_credentials`
    (per-user Deezer Developer App stored in the user database).
    """

    app_id: str
    app_secret: str
    redirect_uri: str
    perms: tuple[str, ...]

    @classmethod
    def from_env(cls) -> DeezerAuthConfig:
        """Create a config from environment variables.

        Expected variables:

        - ``DEEZER_APP_ID`` (required for the shared project app)
        - ``DEEZER_APP_SECRET`` (required for the shared project app)
        - ``DEEZER_REDIRECT_URI`` (required; must match the URL registered in
          your Deezer Developer App's "Application domain"/"Redirect URL").
        - ``DEEZER_PERMS`` (optional, comma separated; defaults to
          ``manage_library,offline_access`` so issued tokens never expire).
        """
        if not getenv("DEEZER_APP_ID"):
            _load_dotenv_keys_if_unset(
                {
                    "DEEZER_APP_ID",
                    "DEEZER_APP_SECRET",
                    "DEEZER_REDIRECT_URI",
                    "DEEZER_PERMS",
                },
            )
        app_id = (getenv("DEEZER_APP_ID") or "").strip()
        app_secret = (getenv("DEEZER_APP_SECRET") or "").strip()
        redirect_raw = (getenv("DEEZER_REDIRECT_URI") or "").strip()
        perms_raw = (getenv("DEEZER_PERMS") or "").strip()

        if not app_id:
            raise DeezerConfigError("DEEZER_APP_ID is not set")
        if not app_secret:
            raise DeezerConfigError("DEEZER_APP_SECRET is not set")
        if not redirect_raw:
            raise DeezerConfigError("DEEZER_REDIRECT_URI is not set")
        redirect_uri = normalize_streamlit_deezer_redirect_uri(redirect_raw)

        perms: tuple[str, ...]
        if perms_raw:
            perms = tuple(
                p.strip() for p in perms_raw.replace(" ", ",").split(",") if p.strip()
            )
        else:
            perms = ("manage_library", "offline_access")

        return cls(
            app_id=app_id,
            app_secret=app_secret,
            redirect_uri=redirect_uri,
            perms=perms,
        )

    @classmethod
    def from_user_credentials(
        cls,
        *,
        app_id: str,
        app_secret: str,
        redirect_uri: str | None = None,
        perms: tuple[str, ...] | None = None,
    ) -> DeezerAuthConfig:
        """Build a config from per-user Deezer Developer App credentials."""
        if not app_id or not app_secret:
            raise DeezerConfigError(
                "Deezer App-ID und App-Secret sind erforderlich.",
            )
        if redirect_uri is None:
            redirect_uri = (getenv("DEEZER_REDIRECT_URI") or "").strip()
        if not redirect_uri:
            raise DeezerConfigError("DEEZER_REDIRECT_URI is not set")
        redirect_uri = normalize_streamlit_deezer_redirect_uri(redirect_uri)
        if perms is None:
            perms = ("manage_library", "offline_access")
        return cls(
            app_id=app_id.strip(),
            app_secret=app_secret.strip(),
            redirect_uri=redirect_uri,
            perms=perms,
        )


@dataclass(slots=True)
class DeezerToken:
    """Access token information for a Deezer user.

    Deezer does not issue refresh tokens. With ``offline_access`` granted, the
    token never expires (``expires_in == 0``); without it, the user must
    authenticate again once :meth:`is_expired` returns ``True``.
    """

    access_token: str
    expires_in: int
    obtained_at: datetime

    @classmethod
    def from_token_response_text(cls, body: str) -> DeezerToken:
        """Parse a Deezer token response (form-encoded plain text)."""
        text = (body or "").strip()
        if not text:
            raise ValueError("Empty Deezer token response")
        # Deezer signals failures with plain ``wrong code``-style messages
        # (sometimes wrapped in ``error_reason=...``); detect those upfront.
        if text.lower().startswith("wrong code"):
            raise ValueError("Deezer token response indicates wrong/expired code")
        parsed = urllib.parse.parse_qs(text, keep_blank_values=True)
        access_token_list = parsed.get("access_token") or []
        if not access_token_list or not access_token_list[0]:
            raise ValueError("Deezer token response missing access_token")
        access_token = access_token_list[0]
        expires_raw = (parsed.get("expires") or ["0"])[0]
        try:
            expires_in = int(expires_raw)
        except (TypeError, ValueError):
            expires_in = 0
        return cls(
            access_token=access_token,
            expires_in=expires_in,
            obtained_at=datetime.now(tz=UTC),
        )

    def is_expired(self, *, leeway_seconds: int = 30) -> bool:
        """Return ``True`` when the token should be considered expired.

        Tokens with ``expires_in == 0`` (issued with ``offline_access``) are
        considered to never expire.
        """
        if self.expires_in <= 0:
            return False
        deadline = self.obtained_at + timedelta(seconds=self.expires_in)
        return datetime.now(tz=UTC) >= deadline - timedelta(seconds=leeway_seconds)


@dataclass(slots=True)
class DeezerTrack:
    """Minimal representation of a Deezer track for UI/playlist use."""

    id: str
    title: str
    artist: str
    album: str | None = None
    link: str | None = None


@dataclass(slots=True)
class DeezerPlaylist:
    """Minimal representation of a Deezer playlist for UI/publish use."""

    id: str
    title: str
    link: str | None = None


def normalize_playlist_display_name_for_match(name: str) -> str:
    """Normalize a playlist title for case-insensitive equality (user library scan)."""
    return unicodedata.normalize("NFKC", name.strip()).casefold()


def deezer_track_uri(track_id: str) -> str:
    """Return a stable opaque track identifier for the catalog cache.

    The pipeline only needs an opaque string per provider; we use the
    ``deezer:track:{id}`` shape so the value never collides with Spotify URIs
    in the shared :mod:`streaming_catalog_cache`.
    """
    return f"deezer:track:{track_id.strip()}"


def deezer_track_id_from_uri(value: str) -> str | None:
    """Extract the numeric Deezer track id from a ``deezer:track:{id}`` string."""
    raw = (value or "").strip()
    prefix = "deezer:track:"
    if not raw.startswith(prefix):
        return None
    rest = raw[len(prefix) :].strip()
    return rest or None


class DeezerClient:
    """High-level client for Deezer REST operations.

    The client is stateless with respect to tokens; the caller is responsible
    for storing :class:`DeezerToken` instances. Bulk operations honour a small
    sleep interval between requests to stay safely below Deezer's IP-based
    rate limit (50 req / 5 s).
    """

    def __init__(self, config: DeezerAuthConfig) -> None:
        self._config = config

    def with_redirect_uri(self, redirect_uri: str) -> DeezerClient:
        """Return a client that uses ``redirect_uri`` for OAuth (authorize+token)."""
        normalized = redirect_uri.strip()
        if not normalized:
            msg = "redirect_uri must be non-empty"
            raise ValueError(msg)
        return DeezerClient(replace(self._config, redirect_uri=normalized))

    @property
    def perms(self) -> tuple[str, ...]:
        """Return configured OAuth permissions."""
        return self._config.perms

    @property
    def redirect_uri(self) -> str:
        """OAuth redirect URI used for authorize and token exchange."""
        return self._config.redirect_uri

    @property
    def app_id(self) -> str:
        """Deezer App-ID currently used for OAuth."""
        return self._config.app_id

    def build_authorize_url(self, *, state: str) -> str:
        """Return the URL to start the Deezer OAuth flow."""
        params = {
            "app_id": self._config.app_id,
            "redirect_uri": self._config.redirect_uri,
            "perms": ",".join(self._config.perms),
            "state": state,
        }
        query = urllib.parse.urlencode(params)
        return f"{DEEZER_AUTH_BASE_URL}/auth.php?{query}"

    def _token_endpoint(self) -> str:
        return f"{DEEZER_AUTH_BASE_URL}/access_token.php"

    def exchange_code_for_token(self, *, code: str) -> DeezerToken:
        """Exchange an authorization code for an access token."""
        params = {
            "app_id": self._config.app_id,
            "secret": self._config.app_secret,
            "code": code,
            "output": "json",
        }
        LOGGER.info("Requesting Deezer access token via authorization_code grant")
        response = requests.get(
            self._token_endpoint(),
            params=params,
            timeout=15,
        )
        if response.status_code != 200:
            detail = _deezer_token_error_message(response)
            LOGGER.error(
                "Deezer token endpoint returned %s: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(detail)
        body = response.text or ""
        return self._parse_token_response(body)

    @staticmethod
    def _parse_token_response(body: str) -> DeezerToken:
        """Parse the Deezer token endpoint body, accepting JSON or form-encoded."""
        text = (body or "").strip()
        if not text:
            raise RuntimeError("Empty Deezer token response")
        if text.startswith("{"):
            # ``output=json`` returned a real JSON document.
            import json

            try:
                payload = json.loads(text)
            except ValueError as exc:
                raise RuntimeError(
                    f"Deezer token response is not valid JSON: {text[:200]}"
                ) from exc
            if isinstance(payload, dict) and "access_token" in payload:
                synthetic = urllib.parse.urlencode(
                    {
                        "access_token": str(payload.get("access_token") or ""),
                        "expires": str(payload.get("expires", "0")),
                    }
                )
                try:
                    return DeezerToken.from_token_response_text(synthetic)
                except ValueError as exc:
                    raise RuntimeError(str(exc)) from exc
            raise RuntimeError(
                f"Deezer token response missing access_token: {text[:200]}"
            )
        try:
            return DeezerToken.from_token_response_text(text)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str | None,
        params: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue a Deezer API request and validate both HTTP and body errors."""
        url = f"{DEEZER_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        full_params: dict[str, Any] = dict(params or {})
        if access_token is not None:
            full_params["access_token"] = access_token
        LOGGER.debug("Deezer API request %s %s", method, url)
        response = requests.request(
            method=method.upper(),
            url=url,
            params=full_params,
            data=body if body else None,
            timeout=15,
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            LOGGER.warning("Deezer API rate limit hit; Retry-After=%s", retry_after)
            raise RuntimeError("Deezer rate limit exceeded; please try again later")
        if not response.ok:
            detail = _deezer_api_error_message(response)
            LOGGER.error(
                "Deezer API error %s for %s %s: %s",
                response.status_code,
                method,
                path,
                response.text,
            )
            raise RuntimeError(detail)
        try:
            parsed = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Deezer API returned non-JSON body: {response.text[:200]}"
            ) from exc
        # Many Deezer endpoints (e.g. ``POST /playlist/{id}/tracks``) return
        # ``true`` or ``false`` instead of a JSON object on success.
        if isinstance(parsed, bool):
            return {"_bool": parsed}
        if not isinstance(parsed, dict):
            raise RuntimeError("Unexpected Deezer API response shape")
        err = parsed.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or "Unknown Deezer API error"
            etype = err.get("type")
            LOGGER.error(
                "Deezer API returned application-level error type=%s message=%s",
                etype,
                msg,
            )
            if isinstance(etype, str) and etype.strip():
                raise RuntimeError(f"Deezer API ({etype.strip()}): {msg}")
            raise RuntimeError(f"Deezer API: {msg}")
        return parsed

    def get_current_user_id(self, *, token: DeezerToken) -> str:
        """Return the numeric Deezer user id for the current access token."""
        data = self._request("GET", "/user/me", access_token=token.access_token)
        user_id = data.get("id")
        if user_id is None:
            raise RuntimeError("Deezer /user/me response missing id")
        return str(user_id)

    @staticmethod
    def build_track_search_query(*, artist: str, title: str) -> str:
        """Compose the ``artist:"…" track:"…"`` query Deezer expects for tracks."""
        a = artist.strip().replace('"', "")
        t = title.strip().replace('"', "")
        if not a and not t:
            return ""
        if not t:
            return f'artist:"{a}"'
        if not a:
            return f'track:"{t}"'
        return f'artist:"{a}" track:"{t}"'

    def search_tracks(
        self,
        *,
        query: str,
        token: DeezerToken,
        limit: int = 20,
    ) -> list[DeezerTrack]:
        """Search for tracks matching the given Deezer-syntax query string."""
        q = query.strip()
        if not q:
            return []
        params: dict[str, Any] = {
            "q": q,
            "limit": max(1, min(int(limit), 50)),
        }
        data = self._request(
            "GET",
            "/search/track",
            access_token=token.access_token,
            params=params,
        )
        items = data.get("data")
        results: list[DeezerTrack] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                track_id = item.get("id")
                title = item.get("title") or item.get("title_short")
                if track_id is None or not isinstance(title, str):
                    continue
                artist_name = ""
                artist_obj = item.get("artist")
                if isinstance(artist_obj, Mapping):
                    aname = artist_obj.get("name")
                    if isinstance(aname, str):
                        artist_name = aname
                album_name: str | None = None
                album_obj = item.get("album")
                if isinstance(album_obj, Mapping):
                    aname2 = album_obj.get("title")
                    if isinstance(aname2, str):
                        album_name = aname2
                link = item.get("link")
                results.append(
                    DeezerTrack(
                        id=str(track_id),
                        title=title,
                        artist=artist_name,
                        album=album_name,
                        link=link if isinstance(link, str) else None,
                    ),
                )
        return results

    def create_playlist(
        self,
        *,
        title: str,
        token: DeezerToken,
    ) -> DeezerPlaylist:
        """Create a new (initially empty) playlist for the current user.

        Deezer creates playlists as ``private`` by default. Use
        :meth:`set_playlist_visibility` to flip the ``public`` flag afterwards.
        """
        if not title.strip():
            raise ValueError("Playlist title must not be empty")
        data = self._request(
            "POST",
            "/user/me/playlists",
            access_token=token.access_token,
            params={"title": title.strip()},
        )
        pid = data.get("id")
        if pid is None:
            raise RuntimeError("Deezer create playlist response missing id")
        return DeezerPlaylist(
            id=str(pid),
            title=title.strip(),
            link=f"https://www.deezer.com/playlist/{pid}",
        )

    def add_tracks_to_playlist(
        self,
        *,
        playlist_id: str,
        track_ids: list[str],
        token: DeezerToken,
        chunk_size: int = 50,
    ) -> None:
        """Append the given Deezer track ids to a playlist (chunked, throttled)."""
        if not track_ids:
            return
        path = f"/playlist/{urllib.parse.quote(playlist_id)}/tracks"
        cleaned = [tid for tid in (str(t).strip() for t in track_ids) if tid]
        if not cleaned:
            return
        for idx in range(0, len(cleaned), chunk_size):
            chunk = cleaned[idx : idx + chunk_size]
            LOGGER.info(
                "Deezer add_tracks_to_playlist: chunk size=%s playlist_id=%s",
                len(chunk),
                playlist_id,
            )
            self._request(
                "POST",
                path,
                access_token=token.access_token,
                params={"songs": ",".join(chunk)},
            )
            if idx + chunk_size < len(cleaned):
                time.sleep(DEEZER_BULK_REQUEST_INTERVAL_SECONDS)

    def remove_tracks_from_playlist(
        self,
        *,
        playlist_id: str,
        track_ids: list[str],
        token: DeezerToken,
        chunk_size: int = 50,
    ) -> None:
        """Remove the given Deezer track ids from a playlist (chunked, throttled)."""
        if not track_ids:
            return
        path = f"/playlist/{urllib.parse.quote(playlist_id)}/tracks"
        cleaned = [tid for tid in (str(t).strip() for t in track_ids) if tid]
        if not cleaned:
            return
        for idx in range(0, len(cleaned), chunk_size):
            chunk = cleaned[idx : idx + chunk_size]
            LOGGER.info(
                "Deezer remove_tracks_from_playlist: chunk size=%s playlist_id=%s",
                len(chunk),
                playlist_id,
            )
            self._request(
                "DELETE",
                path,
                access_token=token.access_token,
                params={"songs": ",".join(chunk)},
            )
            if idx + chunk_size < len(cleaned):
                time.sleep(DEEZER_BULK_REQUEST_INTERVAL_SECONDS)

    def list_playlist_track_ids(
        self,
        *,
        playlist_id: str,
        token: DeezerToken,
    ) -> list[str]:
        """Return all track ids currently inside the given playlist (paginated)."""
        path = f"/playlist/{urllib.parse.quote(playlist_id)}/tracks"
        ids: list[str] = []
        next_url: str | None = None
        params: dict[str, Any] | None = {"limit": 50}
        while True:
            if next_url:
                LOGGER.debug("Deezer list_playlist_tracks following next=%s", next_url)
                resp = requests.get(next_url, timeout=15)
                if not resp.ok:
                    raise RuntimeError(_deezer_api_error_message(resp))
                data: dict[str, Any] = resp.json()
            else:
                data = self._request(
                    "GET",
                    path,
                    access_token=token.access_token,
                    params=params,
                )
            items = data.get("data") if isinstance(data, dict) else None
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, Mapping) and item.get("id") is not None:
                        ids.append(str(item.get("id")))
            next_link = data.get("next") if isinstance(data, dict) else None
            if not isinstance(next_link, str) or not next_link.strip():
                break
            next_url = next_link
            params = None
        return ids

    def set_playlist_visibility(
        self,
        *,
        playlist_id: str,
        public: bool,
        token: DeezerToken,
    ) -> None:
        """Set the ``public`` flag of an owned playlist."""
        path = f"/playlist/{urllib.parse.quote(playlist_id)}"
        LOGGER.info(
            "Deezer set_playlist_visibility playlist_id=%s public=%s",
            playlist_id,
            public,
        )
        self._request(
            "POST",
            path,
            access_token=token.access_token,
            params={"public": "true" if public else "false"},
        )

    def find_owned_playlist_id_by_display_name(
        self,
        *,
        display_name: str,
        token: DeezerToken,
    ) -> str | None:
        """Return the first owned playlist id whose title matches ``display_name``."""
        target = normalize_playlist_display_name_for_match(display_name)
        if not target:
            return None
        path = "/user/me/playlists"
        next_url: str | None = None
        params: dict[str, Any] | None = {"limit": 50}
        LOGGER.info(
            "Scanning Deezer user playlists for display name match (limit=50)",
        )
        while True:
            if next_url:
                resp = requests.get(next_url, timeout=15)
                if not resp.ok:
                    raise RuntimeError(_deezer_api_error_message(resp))
                data: dict[str, Any] = resp.json()
            else:
                data = self._request(
                    "GET",
                    path,
                    access_token=token.access_token,
                    params=params,
                )
            items = data.get("data") if isinstance(data, dict) else None
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, Mapping):
                        continue
                    pname = item.get("title")
                    pid = item.get("id")
                    if pid is None or not isinstance(pname, str):
                        continue
                    if normalize_playlist_display_name_for_match(pname) == target:
                        LOGGER.info(
                            "Found owned Deezer playlist id=%s title=%r",
                            pid,
                            pname,
                        )
                        return str(pid)
            next_link = data.get("next") if isinstance(data, dict) else None
            if not isinstance(next_link, str) or not next_link.strip():
                break
            next_url = next_link
            params = None
        return None

    def replace_all_playlist_tracks(
        self,
        *,
        playlist_id: str,
        track_ids: list[str],
        token: DeezerToken,
    ) -> None:
        """Clear an owned playlist and append ``track_ids`` in the given order."""
        existing = self.list_playlist_track_ids(
            playlist_id=playlist_id,
            token=token,
        )
        if existing:
            LOGGER.info(
                "replace_all_playlist_tracks: removing n=%s existing tracks",
                len(existing),
            )
            self.remove_tracks_from_playlist(
                playlist_id=playlist_id,
                track_ids=existing,
                token=token,
            )
        if track_ids:
            self.add_tracks_to_playlist(
                playlist_id=playlist_id,
                track_ids=track_ids,
                token=token,
            )

    def get_playlist(
        self,
        *,
        playlist_id: str,
        token: DeezerToken,
    ) -> DeezerPlaylist:
        """Load playlist id, title, and external Deezer URL."""
        data = self._request(
            "GET",
            f"/playlist/{urllib.parse.quote(playlist_id)}",
            access_token=token.access_token,
        )
        pid = data.get("id")
        title = data.get("title")
        link = data.get("link")
        if pid is None or not isinstance(title, str):
            raise RuntimeError("Deezer get playlist response missing id/title")
        return DeezerPlaylist(
            id=str(pid),
            title=title,
            link=link if isinstance(link, str) else None,
        )
