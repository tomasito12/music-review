from __future__ import annotations

# Typed client wrapper for the Spotify Web API.
# Network I/O uses ``requests`` and configuration is read from environment
# variables so it can be controlled via the existing ``.env`` mechanism.
import base64
import hashlib
import logging
import secrets
import urllib.parse
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import getenv
from typing import Any, Final

import requests

LOGGER: Final = logging.getLogger(__name__)

SPOTIFY_AUTH_BASE_URL: Final = "https://accounts.spotify.com"
SPOTIFY_API_BASE_URL: Final = "https://api.spotify.com/v1"


class SpotifyConfigError(RuntimeError):
    """Raised when required Spotify configuration is missing or invalid."""


@dataclass(slots=True)
class SpotifyAuthConfig:
    """Static configuration for Spotify OAuth.

    Instances of this class are usually created via
    :func:`SpotifyAuthConfig.from_env`.
    """

    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
    client_secret: str | None = None

    @classmethod
    def from_env(cls) -> SpotifyAuthConfig:
        """Create a config from environment variables.

        Expected variables:

        - ``SPOTIFY_CLIENT_ID`` (required)
        - ``SPOTIFY_REDIRECT_URI`` (required)
        - ``SPOTIFY_SCOPES`` (optional, space-separated)
        - ``SPOTIFY_CLIENT_SECRET`` (optional, only used for some flows)
        """
        client_id = (getenv("SPOTIFY_CLIENT_ID") or "").strip()
        redirect_uri = (getenv("SPOTIFY_REDIRECT_URI") or "").strip()
        scopes_raw = (getenv("SPOTIFY_SCOPES") or "").strip()
        client_secret = (getenv("SPOTIFY_CLIENT_SECRET") or "").strip() or None

        if not client_id:
            raise SpotifyConfigError("SPOTIFY_CLIENT_ID is not set")
        if not redirect_uri:
            raise SpotifyConfigError("SPOTIFY_REDIRECT_URI is not set")

        scopes: tuple[str, ...]
        if scopes_raw:
            scopes = tuple(scope for scope in scopes_raw.split() if scope)
        else:
            scopes = (
                "playlist-modify-public",
                "playlist-modify-private",
            )

        return cls(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            client_secret=client_secret,
        )


@dataclass(slots=True)
class SpotifyToken:
    """Access and refresh token information for a Spotify user."""

    access_token: str
    token_type: str
    expires_at: datetime
    refresh_token: str | None = None
    scope: str | None = None

    @classmethod
    def from_token_response(cls, data: Mapping[str, Any]) -> SpotifyToken:
        """Build a :class:`SpotifyToken` instance from a Spotify token response."""
        access_token = str(data.get("access_token") or "")
        token_type = str(data.get("token_type") or "Bearer")
        expires_in_raw = data.get("expires_in")
        refresh_token_val = data.get("refresh_token")
        scope = data.get("scope")

        if not access_token:
            raise ValueError("Token response missing access_token")

        try:
            expires_in = int(expires_in_raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            expires_in = 3600

        expires_at = datetime.now(tz=UTC) + timedelta(seconds=expires_in)

        refresh_token: str | None
        if isinstance(refresh_token_val, str) and refresh_token_val:
            refresh_token = refresh_token_val
        else:
            refresh_token = None

        scope_str: str | None = scope if isinstance(scope, str) and scope else None

        return cls(
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            refresh_token=refresh_token,
            scope=scope_str,
        )

    def is_expired(self, *, leeway_seconds: int = 30) -> bool:
        """Return ``True`` if the token should be considered expired."""
        now = datetime.now(tz=UTC)
        return now >= self.expires_at - timedelta(seconds=leeway_seconds)


@dataclass(slots=True)
class SpotifyTrack:
    """Minimal representation of a track for UI use."""

    id: str
    name: str
    uri: str
    artists: tuple[str, ...]
    album_name: str | None = None


@dataclass(slots=True)
class SpotifyArtist:
    """Minimal representation of an artist for UI use."""

    id: str
    name: str
    uri: str


@dataclass(slots=True)
class SpotifyPlaylist:
    """Minimal representation of a playlist for UI use."""

    id: str
    name: str
    uri: str
    external_url: str | None = None


def generate_pkce_pair() -> tuple[str, str]:
    """Return a ``(code_verifier, code_challenge)`` PKCE pair.

    The verifier is a high-entropy random string, the challenge is the
    base64url-encoded SHA256 hash of the verifier without padding.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


class SpotifyClient:
    """High-level client for Spotify Web API operations.

    The client is stateless with respect to tokens; the caller is responsible
    for storing :class:`SpotifyToken` instances (e.g. in Streamlit session
    state).
    """

    def __init__(self, config: SpotifyAuthConfig) -> None:
        self._config = config

    @property
    def scopes(self) -> tuple[str, ...]:
        """Return configured OAuth scopes."""
        return self._config.scopes

    def build_authorize_url(
        self,
        *,
        state: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
    ) -> str:
        """Return the URL to start the Spotify OAuth flow with PKCE enabled."""
        params = {
            "client_id": self._config.client_id,
            "response_type": "code",
            "redirect_uri": self._config.redirect_uri,
            "scope": " ".join(self._config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }
        query = urllib.parse.urlencode(params)
        return f"{SPOTIFY_AUTH_BASE_URL}/authorize?{query}"

    def _token_endpoint(self) -> str:
        return f"{SPOTIFY_AUTH_BASE_URL}/api/token"

    def exchange_code_for_token(
        self,
        *,
        code: str,
        code_verifier: str,
    ) -> SpotifyToken:
        """Exchange an authorization code for an access/refresh token pair."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._config.redirect_uri,
            "client_id": self._config.client_id,
            "code_verifier": code_verifier,
        }
        headers: dict[str, str] = {}
        if self._config.client_secret:
            # Some environments still prefer basic auth with client secret.
            basic = f"{self._config.client_id}:{self._config.client_secret}"
            b64 = base64.b64encode(basic.encode("ascii")).decode("ascii")
            headers["Authorization"] = f"Basic {b64}"

        LOGGER.info("Requesting Spotify access token via authorization_code grant")
        response = requests.post(
            self._token_endpoint(),
            data=data,
            headers=headers,
            timeout=15,
        )
        if response.status_code != 200:
            LOGGER.error(
                "Spotify token endpoint returned %s: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                "Failed to exchange Spotify authorization code for token",
            )
        payload = response.json()
        return SpotifyToken.from_token_response(payload)

    def refresh_access_token(self, refresh_token: str) -> SpotifyToken:
        """Refresh an access token using a stored refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self._config.client_id,
        }
        headers: dict[str, str] = {}
        if self._config.client_secret:
            basic = f"{self._config.client_id}:{self._config.client_secret}"
            b64 = base64.b64encode(basic.encode("ascii")).decode("ascii")
            headers["Authorization"] = f"Basic {b64}"

        LOGGER.info("Refreshing Spotify access token")
        response = requests.post(
            self._token_endpoint(),
            data=data,
            headers=headers,
            timeout=15,
        )
        if response.status_code != 200:
            LOGGER.error(
                "Spotify token refresh failed with %s: %s",
                response.status_code,
                response.text,
            )
            raise RuntimeError("Failed to refresh Spotify access token")
        payload = response.json()
        # Spotify may omit refresh_token in refresh responses; preserve the old one.
        token = SpotifyToken.from_token_response(payload)
        if token.refresh_token is None:
            token.refresh_token = refresh_token
        return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{SPOTIFY_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        LOGGER.debug("Spotify API request %s %s", method, url)
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=15,
        )
        if response.status_code == 401:
            LOGGER.warning("Spotify API returned 401 (unauthorized)")
            raise RuntimeError("Spotify access token is invalid or expired")
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            LOGGER.warning("Spotify API rate limit hit; Retry-After=%s", retry_after)
            raise RuntimeError("Spotify rate limit exceeded; please try again later")
        if not response.ok:
            LOGGER.error(
                "Spotify API error %s for %s %s: %s",
                response.status_code,
                method,
                path,
                response.text,
            )
            raise RuntimeError("Spotify API request failed")
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise RuntimeError("Unexpected Spotify API response shape")
        return parsed

    def get_current_user_id(self, *, token: SpotifyToken) -> str:
        """Return the Spotify user id for the current access token."""
        data = self._request("GET", "/me", access_token=token.access_token)
        user_id = data.get("id")
        if not isinstance(user_id, str) or not user_id:
            raise RuntimeError("Spotify /me response missing id")
        return user_id

    def search_tracks(
        self,
        *,
        query: str,
        limit: int = 20,
        token: SpotifyToken,
    ) -> list[SpotifyTrack]:
        """Search for tracks matching the given query string."""
        q = query.strip()
        if not q:
            return []
        params: dict[str, Any] = {
            "q": q,
            "type": "track",
            "limit": max(1, min(int(limit), 50)),
        }
        data = self._request(
            "GET",
            "/search",
            access_token=token.access_token,
            params=params,
        )
        tracks_obj = data.get("tracks") or {}
        items = tracks_obj.get("items") if isinstance(tracks_obj, Mapping) else None
        results: list[SpotifyTrack] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                track_id = item.get("id")
                name = item.get("name")
                uri = item.get("uri")
                if not (
                    isinstance(track_id, str)
                    and isinstance(name, str)
                    and isinstance(uri, str)
                ):
                    continue
                album_name: str | None = None
                album = item.get("album")
                if isinstance(album, Mapping):
                    album_name_val = album.get("name")
                    if isinstance(album_name_val, str):
                        album_name = album_name_val
                artists_field = item.get("artists")
                artists: list[str] = []
                if isinstance(artists_field, list):
                    for a in artists_field:
                        if isinstance(a, Mapping):
                            aname = a.get("name")
                            if isinstance(aname, str):
                                artists.append(aname)
                results.append(
                    SpotifyTrack(
                        id=track_id,
                        name=name,
                        uri=uri,
                        artists=tuple(artists),
                        album_name=album_name,
                    ),
                )
        return results

    def search_artists(
        self,
        *,
        query: str,
        limit: int = 20,
        token: SpotifyToken,
    ) -> list[SpotifyArtist]:
        """Search for artists matching the given query string."""
        q = query.strip()
        if not q:
            return []
        params: dict[str, Any] = {
            "q": q,
            "type": "artist",
            "limit": max(1, min(int(limit), 50)),
        }
        data = self._request(
            "GET",
            "/search",
            access_token=token.access_token,
            params=params,
        )
        artists_obj = data.get("artists") or {}
        items = artists_obj.get("items") if isinstance(artists_obj, Mapping) else None
        results: list[SpotifyArtist] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                artist_id = item.get("id")
                name = item.get("name")
                uri = item.get("uri")
                if not (
                    isinstance(artist_id, str)
                    and isinstance(name, str)
                    and isinstance(uri, str)
                ):
                    continue
                results.append(
                    SpotifyArtist(
                        id=artist_id,
                        name=name,
                        uri=uri,
                    ),
                )
        return results

    def create_playlist(
        self,
        *,
        user_id: str,
        name: str,
        public: bool,
        token: SpotifyToken,
        description: str | None = None,
    ) -> SpotifyPlaylist:
        """Create a new playlist for the given user."""
        payload: dict[str, Any] = {
            "name": name,
            "public": bool(public),
        }
        if description:
            payload["description"] = description
        path = f"/users/{urllib.parse.quote(user_id)}/playlists"
        data = self._request(
            "POST",
            path,
            access_token=token.access_token,
            json_body=payload,
        )
        pid = data.get("id")
        pname = data.get("name")
        uri = data.get("uri")
        if not (
            isinstance(pid, str) and isinstance(pname, str) and isinstance(uri, str)
        ):
            raise RuntimeError("Spotify create playlist response missing id/name/uri")
        external_url: str | None = None
        ext_urls = data.get("external_urls")
        if isinstance(ext_urls, Mapping):
            spotify_url = ext_urls.get("spotify")
            if isinstance(spotify_url, str):
                external_url = spotify_url
        return SpotifyPlaylist(
            id=pid,
            name=pname,
            uri=uri,
            external_url=external_url,
        )

    def add_tracks_to_playlist(
        self,
        *,
        playlist_id: str,
        track_uris: list[str],
        token: SpotifyToken,
    ) -> None:
        """Append the given tracks to a playlist."""
        if not track_uris:
            return
        payload = {"uris": list(track_uris)}
        path = f"/playlists/{urllib.parse.quote(playlist_id)}/tracks"
        self._request(
            "POST",
            path,
            access_token=token.access_token,
            json_body=payload,
        )
