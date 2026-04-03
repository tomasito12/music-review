"""Spotify playlist builder UI for newest reviews (Streamlit; German user strings)."""

from __future__ import annotations

import random
import secrets
from datetime import date
from typing import Any

import streamlit as st

from music_review.dashboard.newest_spotify_playlist import (
    PlaylistCandidate,
    build_album_weights,
    build_playlist_candidates,
    resolve_track_uri_strict,
)
from music_review.domain.models import Review
from music_review.integrations.spotify_client import (
    SpotifyAuthConfig,
    SpotifyClient,
    SpotifyConfigError,
    SpotifyToken,
)

SPOTIFY_TOKEN_KEY = "spotify_token"
NEWEST_SPOTIFY_PREVIEW_KEY = "newest_spotify_preview"
NEWEST_SPOTIFY_PLAYLIST_NAME_KEY = "newest-spotify-playlist-name"


def _default_newest_spotify_playlist_name() -> str:
    """Default Spotify playlist label: Plattenradar YYYY-MM-DD (local date)."""
    return f"Plattenradar {date.today().isoformat()}"


def _stored_spotify_token() -> SpotifyToken | None:
    raw = st.session_state.get(SPOTIFY_TOKEN_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        return SpotifyToken(
            access_token=str(raw["access_token"]),
            token_type=str(raw.get("token_type", "Bearer")),
            expires_at=raw["expires_at"],
            refresh_token=raw.get("refresh_token"),
            scope=raw.get("scope"),
        )
    except Exception:
        return None


def _store_spotify_token(token: SpotifyToken) -> None:
    st.session_state[SPOTIFY_TOKEN_KEY] = {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "expires_at": token.expires_at,
        "refresh_token": token.refresh_token,
        "scope": token.scope,
    }


def _ensure_valid_spotify_token(
    client: SpotifyClient,
    token: SpotifyToken,
) -> SpotifyToken:
    """Return a usable token and refresh it when required."""
    if not token.is_expired():
        return token
    if not token.refresh_token:
        raise RuntimeError(
            "Die Spotify-Sitzung ist abgelaufen. Bitte erneut auf "
            "„Mit Spotify verbinden“ klicken."
        )
    refreshed = client.refresh_access_token(refresh_token=token.refresh_token)
    _store_spotify_token(refreshed)
    return refreshed


def _token_declares_spotify_scope(token: SpotifyToken, scope: str) -> bool:
    """Return True if the granted scope string from Spotify lists ``scope``."""
    granted = {s for s in (token.scope or "").split() if s}
    return scope in granted


def _render_playlist_preview_table(items: list[PlaylistCandidate]) -> None:
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        rows.append(
            {
                "#": idx,
                "Künstler": item.artist,
                "Album": item.album,
                "Song": item.track_title,
                "Quelle": (
                    "Highlight" if item.source_kind == "highlight" else "Tracklist"
                ),
                "Spotify URI": item.spotify_uri,
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)


def render_neueste_spotify_playlist_section(
    *,
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
) -> None:
    """Expander: build a random playlist from the same pool as Neueste Rezensionen."""
    with st.expander("Spotify-Playlist aus den neuesten Rezensionen", expanded=False):
        st.caption(
            "Erzeuge eine zufällige Playlist auf Basis der aktuell "
            "angezeigten neuesten Rezensionen."
        )
        st.caption(
            "Gewichtung: Pro Slot wird ein Album mit Zurücklegen gezogen; "
            "die Wahrscheinlichkeiten verhalten sich wie die angezeigten "
            "Scores (jeder Score geteilt durch die Summe aller Scores im Pool). "
            "Pro Album werden zuerst zufällig Anspieltipps genutzt, danach "
            "übrige Titel. Wenn Spotify einen Titel nicht eindeutig findet, "
            "wird er übersprungen und neu gezogen; Alben mit zuverlässigeren "
            "Treffern können deshalb in der fertigen Liste häufiger vorkommen."
        )
        if not reviews:
            st.info("Keine Rezensionen verfügbar.")
            return

        max_pool = len(reviews)
        target_count = st.slider(
            "Zielanzahl Songs",
            min_value=5,
            max_value=50,
            value=min(30, max(5, max_pool)),
            step=1,
        )
        pool_count = st.slider(
            "Wie viele der angezeigten neuesten Rezensionen berücksichtigen",
            min_value=1,
            max_value=max_pool,
            value=max_pool,
            step=1,
        )
        if NEWEST_SPOTIFY_PLAYLIST_NAME_KEY not in st.session_state:
            st.session_state[NEWEST_SPOTIFY_PLAYLIST_NAME_KEY] = (
                _default_newest_spotify_playlist_name()
            )
        playlist_name = st.text_input(
            "Name der Spotify-Playlist",
            key=NEWEST_SPOTIFY_PLAYLIST_NAME_KEY,
        )
        make_playlist_public = st.checkbox(
            "Playlist öffentlich machen",
            value=False,
            key="newest-spotify-playlist-public",
        )

        token = _stored_spotify_token()
        if token is None:
            st.info(
                "Bitte zuerst oben auf dieser Seite mit Spotify verbinden, "
                "damit eine Playlist gespeichert werden kann."
            )
            return

        pool_reviews = reviews[:pool_count]
        pool_rows = ranked_rows[:pool_count] if ranked_rows else None
        chosen_reviews, weights = build_album_weights(pool_reviews, pool_rows)
        client: SpotifyClient | None = None
        config_error: str | None = None
        try:
            client = SpotifyClient(SpotifyAuthConfig.from_env())
        except SpotifyConfigError as exc:
            config_error = str(exc)

        col_generate, col_regenerate = st.columns(2)
        if config_error:
            st.error(f"Spotify-Konfiguration fehlt: {config_error}")
            return
        assert client is not None

        with col_generate:
            generate_clicked = st.button(
                "Vorschau erzeugen",
                type="primary",
                key="newest-spotify-generate",
                width="stretch",
            )
        with col_regenerate:
            regenerate_clicked = st.button(
                "Nochmal erzeugen",
                key="newest-spotify-regenerate",
                width="stretch",
            )

        scope_check_token = _stored_spotify_token()
        if (
            scope_check_token is not None
            and not make_playlist_public
            and not _token_declares_spotify_scope(
                scope_check_token,
                "playlist-modify-private",
            )
        ):
            st.warning(
                "Für eine private Playlist braucht Spotify das OAuth-Scope "
                "„playlist-modify-private“. Ohne dieses Recht antwortet die API "
                "oft mit 403 Forbidden. Bitte Verbindung trennen und erneut "
                "verbinden, und in der `.env` sicherstellen, dass "
                "`SPOTIFY_SCOPES` dieses Scope enthält."
            )
        if (
            scope_check_token is not None
            and make_playlist_public
            and not _token_declares_spotify_scope(
                scope_check_token,
                "playlist-modify-public",
            )
        ):
            st.warning(
                "Für eine öffentliche Playlist braucht Spotify das Scope "
                "„playlist-modify-public“. Bitte Verbindung erneuern oder "
                "`SPOTIFY_SCOPES` in der `.env` prüfen."
            )

        if generate_clicked or regenerate_clicked:
            rng = random.Random(secrets.randbits(64))
            with st.spinner("Playlist-Vorschau wird erzeugt..."):
                token_for_search = _ensure_valid_spotify_token(client, token)
                preview = build_playlist_candidates(
                    reviews=chosen_reviews,
                    weights=weights,
                    target_count=target_count,
                    rng=rng,
                    resolve_fn=lambda *, artist, track_title: resolve_track_uri_strict(
                        client,
                        token_for_search,
                        artist=artist,
                        track_title=track_title,
                    ),
                )
            st.session_state[NEWEST_SPOTIFY_PREVIEW_KEY] = preview

        preview_items_any = st.session_state.get(NEWEST_SPOTIFY_PREVIEW_KEY)
        preview_items = preview_items_any if isinstance(preview_items_any, list) else []
        valid_preview_items = [
            x for x in preview_items if isinstance(x, PlaylistCandidate)
        ]
        if valid_preview_items:
            _render_playlist_preview_table(valid_preview_items)
            if len(valid_preview_items) < target_count:
                st.warning(
                    "Es konnten nicht genug eindeutige Spotify-Treffer "
                    "gefunden werden. "
                    f"Gefunden: {len(valid_preview_items)} von {target_count}."
                )
            if st.button(
                "Als Spotify-Playlist speichern",
                key="newest-spotify-save",
                width="stretch",
            ):
                try:
                    with st.spinner("Spotify-Playlist wird gespeichert..."):
                        token_for_save = _ensure_valid_spotify_token(client, token)
                        playlist = client.create_playlist(
                            name=playlist_name.strip()
                            or _default_newest_spotify_playlist_name(),
                            description=(
                                "Automatisch erstellt aus den neuesten Rezensionen "
                                "in Music Review."
                            ),
                            public=make_playlist_public,
                            token=token_for_save,
                        )
                        uris = [item.spotify_uri for item in valid_preview_items]
                        for idx in range(0, len(uris), 100):
                            client.add_tracks_to_playlist(
                                playlist_id=playlist.id,
                                track_uris=uris[idx : idx + 100],
                                token=token_for_save,
                            )
                    st.success("Spotify-Playlist erfolgreich gespeichert.")
                except RuntimeError as exc:
                    st.error(
                        "Spotify-Playlist konnte nicht gespeichert werden. "
                        "Bitte Spotify-Verbindung prüfen und erneut versuchen."
                    )
                    st.caption(f"Technische Details: {exc}")
                    detail = str(exc)
                    if "403" in detail or "forbidden" in detail.casefold():
                        st.caption(
                            "Hinweis: HTTP 403 bei Spotify bedeutet oft fehlende "
                            "OAuth-Berechtigungen (z. B. private Playlist ohne "
                            "„playlist-modify-private“). Verbindung trennen, "
                            "`.env`/`SPOTIFY_SCOPES` prüfen, erneut verbinden, "
                            "oder die Option „Playlist öffentlich machen“ testen."
                        )
        else:
            st.caption("Noch keine Vorschau erzeugt.")
