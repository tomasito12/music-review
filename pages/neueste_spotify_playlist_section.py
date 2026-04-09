"""Spotify playlist builder UI for newest reviews (Streamlit; German user strings)."""

from __future__ import annotations

import logging
import random
import secrets
from datetime import UTC, date, datetime
from typing import Any

import streamlit as st
from pages.neueste_reviews_pool import (
    configure_spotify_playlist_logging_from_env,
    preference_rank_rows_for_reviews,
)

from music_review.dashboard.newest_spotify_playlist import (
    PlaylistCandidate,
    amplify_preference_weights,
    build_album_weights,
    build_playlist_candidates,
    resolve_track_uri_strict,
)
from music_review.dashboard.user_profile_store import (
    SPOTIFY_PREVIEW_COOLDOWN_SECONDS,
    default_profiles_dir,
    get_spotify_preview_last_generated_at,
    record_spotify_preview_generated,
    spotify_preview_cooldown_seconds_remaining,
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

_LOGGER = logging.getLogger(__name__)


def _german_cooldown_hint(seconds_remaining: int) -> str:
    """User-facing countdown for the Spotify preview rate limit."""
    if seconds_remaining <= 0:
        return ""
    minutes, secs = divmod(seconds_remaining, 60)
    parts: list[str] = []
    if minutes > 0:
        parts.append("1 Minute" if minutes == 1 else f"{minutes} Minuten")
    if secs > 0 or not parts:
        parts.append("1 Sekunde" if secs == 1 else f"{secs} Sekunden")
    duration = " und ".join(parts) if len(parts) > 1 else parts[0]
    return (
        f"Nächste Vorschau frühestens in {duration} "
        f"(Sperre {SPOTIFY_PREVIEW_COOLDOWN_SECONDS // 60} Minuten nach "
        "„Vorschau erzeugen“; gespeichert im Profil bzw. in dieser Sitzung)."
    )


def _log_weight_summary(weights: list[float], *, review_ids: list[int]) -> None:
    """Emit DEBUG lines for normalized album sampling weights."""
    if not weights:
        _LOGGER.debug("playlist section: no album weights (empty pool)")
        return
    uniform = len(set(round(w, 12) for w in weights)) <= 1
    _LOGGER.debug(
        "playlist section: album_weights n=%s uniform=%s min=%.6f max=%.6f "
        "review_ids_head=%s",
        len(weights),
        uniform,
        min(weights),
        max(weights),
        review_ids[:12],
    )


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


def _render_playlist_preview_table(
    items: list[PlaylistCandidate],
    *,
    target_count: int,
) -> None:
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        w = float(item.score_weight)
        ideal = float(item.strat_ideal_slots)
        rows.append(
            {
                "#": idx,
                "Künstler": item.artist,
                "Album": item.album,
                "Rohscore": round(float(item.raw_score), 4),
                "Anteil (norm.)": round(w, 4),
                "Ziel * Anteil": f"{target_count} * {w:.4f} = {round(ideal, 4)}",
                "Ideale Slots": round(ideal, 4),
                "Abrunden": int(item.strat_floor_slots),
                "+Rest": int(item.strat_remainder_extra_slots),
                "Ziel-Slots": int(item.playlist_slot_quota),
                "Song": item.track_title,
                "Quelle": (
                    "Highlight" if item.source_kind == "highlight" else "Tracklist"
                ),
                "Spotify URI": item.spotify_uri,
            }
        )
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption(
        "Ideale Slots = Zielanzahl mal Anteil; falls die Anteile nicht exakt Summe 1 "
        "haben: Zielanzahl mal (Anteil / Summe). Abrunden ist der ganzzahlige Anteil "
        "davon. +Rest verteilt die noch fehlenden Plätze nach dem größten Rest "
        "(bei Gleichstand höherer Album-Index zuerst). Ziel-Slots = Abrunden + Rest."
    )


def render_neueste_spotify_playlist_section(
    *,
    reviews: list[Review],
) -> None:
    """Build a random playlist from the same pool as Neueste Rezensionen."""
    configure_spotify_playlist_logging_from_env()
    st.caption(
        "Erzeuge eine zufällige Playlist aus den gewählten zuletzt rezensierten "
        "Alben. Präferenz-Scores (wie auf „Neueste Rezensionen“) werden beim "
        "Klick auf „Vorschau erzeugen“ berechnet."
    )
    st.caption(
        "Gewichtung: Die Zielanzahl Songs wird auf die Alben verteilt "
        "entsprechend der normalisierten Scores (Summe 1; Abrundung mit "
        "größtem Rest). Pro Album werden Titel zufällig aus den "
        "Anspieltipps gewählt, danach zufällig aus der übrigen Tracklist. "
        "Die Reihenfolge der Slots ist gemischt. Wenn Spotify einen Titel "
        "nicht findet oder doppelt vorkommt, gibt es nur wenige Wiederholungen "
        "pro Album; danach wird derselbe Listenplatz mit dem nächsten Album "
        "im Pool versucht. Ohne passendes Album wird der Slot verworfen. "
        "Die Liste kann dadurch kürzer als die Zielanzahl werden; die "
        "Verteilung weicht ab, wenn viele Titel nicht aufgelöst werden."
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
    boost_high_scores = st.checkbox(
        "Höhere Ranking-Scores stärker gewichten (mehr Slots für Top-Alben)",
        value=False,
        key="newest-spotify-boost-high-scores",
        help=(
            "Die normalisierten Anteile werden vor der Slot-Verteilung quadriert "
            "und erneut auf Summe 1 gebracht. Dadurch rücken Alben mit hohem "
            "Score näher an die Spitze der Playlist-Quote. "
            "Ohne Ranking (gleichmäßige Gewichte) bleibt die Verteilung "
            "unverändert."
        ),
    )

    token = _stored_spotify_token()
    if token is None:
        st.info(
            "Bitte zuerst oben auf dieser Seite mit Spotify verbinden, "
            "damit eine Playlist gespeichert werden kann."
        )
        return

    client: SpotifyClient | None = None
    config_error: str | None = None
    try:
        client = SpotifyClient(SpotifyAuthConfig.from_env())
    except SpotifyConfigError as exc:
        config_error = str(exc)

    if config_error:
        st.error(f"Spotify-Konfiguration fehlt: {config_error}")
        return
    assert client is not None

    profiles_dir = default_profiles_dir()
    now_utc = datetime.now(UTC)
    last_preview_at = get_spotify_preview_last_generated_at(
        session=st.session_state,
        profiles_dir=profiles_dir,
    )
    cooldown_remaining = spotify_preview_cooldown_seconds_remaining(
        now_utc=now_utc,
        last_generated_at_utc=last_preview_at,
    )
    can_start_preview = cooldown_remaining == 0

    if cooldown_remaining > 0:
        st.warning(_german_cooldown_hint(cooldown_remaining))

    generate_clicked = st.button(
        "Vorschau erzeugen",
        type="primary",
        key="newest-spotify-generate",
        width="stretch",
        disabled=not can_start_preview,
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

    if generate_clicked:
        if not can_start_preview:
            st.warning(
                "Eine neue Vorschau ist noch nicht möglich. Bitte die angezeigte "
                "Wartezeit abwarten.",
            )
        else:
            ranked_rows = preference_rank_rows_for_reviews(reviews)
            chosen_reviews, weights, raw_scores = build_album_weights(
                reviews,
                ranked_rows,
            )
            _LOGGER.info(
                "newest spotify playlist section: n_chosen_albums=%s "
                "ranked_rows_available=%s target_songs=%s",
                len(chosen_reviews),
                ranked_rows is not None,
                target_count,
            )
            _log_weight_summary(
                weights,
                review_ids=[int(r.id) for r in chosen_reviews],
            )
            rng = random.Random(secrets.randbits(64))
            alloc_weights = (
                amplify_preference_weights(weights, exponent=2.0)
                if boost_high_scores
                else weights
            )
            _LOGGER.info(
                "newest spotify preview: start build_playlist_candidates "
                "n_albums=%s target_count=%s boost_high_scores=%s",
                len(chosen_reviews),
                target_count,
                boost_high_scores,
            )
            with st.spinner("Playlist-Vorschau wird erzeugt..."):
                token_for_search = _ensure_valid_spotify_token(client, token)
                preview = build_playlist_candidates(
                    reviews=chosen_reviews,
                    weights=alloc_weights,
                    raw_scores=raw_scores,
                    target_count=target_count,
                    rng=rng,
                    resolve_fn=lambda *, artist, track_title: resolve_track_uri_strict(
                        client,
                        token_for_search,
                        artist=artist,
                        track_title=track_title,
                    ),
                )
            _LOGGER.info(
                "newest spotify preview: finished n_candidates=%s (target was %s)",
                len(preview),
                target_count,
            )
            _LOGGER.debug(
                "newest spotify preview: candidate review_ids=%s",
                [c.review_id for c in preview[:25]],
            )
            st.session_state[NEWEST_SPOTIFY_PREVIEW_KEY] = preview
            record_spotify_preview_generated(
                session=st.session_state,
                profiles_dir=profiles_dir,
                when_utc=datetime.now(UTC),
            )

    preview_items_any = st.session_state.get(NEWEST_SPOTIFY_PREVIEW_KEY)
    preview_items = preview_items_any if isinstance(preview_items_any, list) else []
    valid_preview_items = [x for x in preview_items if isinstance(x, PlaylistCandidate)]
    if valid_preview_items:
        _render_playlist_preview_table(
            valid_preview_items,
            target_count=target_count,
        )
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
                    save_name = (
                        playlist_name.strip() or _default_newest_spotify_playlist_name()
                    )
                    _LOGGER.info(
                        "newest spotify save: create_playlist name=%r public=%s "
                        "n_tracks=%s",
                        save_name,
                        make_playlist_public,
                        len(valid_preview_items),
                    )
                    playlist = client.create_playlist(
                        name=save_name,
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
                    _LOGGER.info(
                        "newest spotify save: done playlist_id=%s url=%r",
                        playlist.id,
                        playlist.external_url,
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
