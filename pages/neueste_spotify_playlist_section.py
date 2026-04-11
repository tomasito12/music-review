"""Spotify playlist builder UI for newest reviews (Streamlit; German user strings)."""

from __future__ import annotations

import logging
import random
import secrets
import threading
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from pages.neueste_reviews_pool import (
    configure_spotify_playlist_logging_from_env,
    preference_rank_rows_for_reviews,
)
from pages.spotify_oauth_kickoff import render_spotify_login_link_under_preview
from pages.spotify_token_persist import (
    persist_spotify_token,
    read_spotify_token_from_session,
)

from music_review.dashboard.neueste_spotify_generate_job import (
    NeuesteSpotifyGenerateOutcome,
    run_neueste_spotify_publish_pipeline,
)
from music_review.dashboard.newest_spotify_playlist import (
    amplify_preference_weights,
    build_album_weights,
)
from music_review.dashboard.user_db import (
    get_connection as get_db_connection,
)
from music_review.dashboard.user_db import (
    load_spotify_credentials,
)
from music_review.dashboard.user_profile_store import (
    ACTIVE_PROFILE_SESSION_KEY,
    default_profiles_dir,
    get_spotify_preview_last_generated_at,
    normalize_profile_slug,
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


def _try_load_user_spotify_config() -> SpotifyAuthConfig | None:
    """Load Spotify config from the logged-in user's DB credentials."""
    raw = st.session_state.get(ACTIVE_PROFILE_SESSION_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        slug = normalize_profile_slug(raw)
    except ValueError:
        return None
    conn = get_db_connection()
    creds = load_spotify_credentials(conn, slug)
    if creds is None:
        return None
    client_id, client_secret = creds
    try:
        return SpotifyAuthConfig.from_user_credentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    except SpotifyConfigError:
        return None


NEWEST_SPOTIFY_PLAYLIST_NAME_KEY = "newest-spotify-playlist-name"
NEWEST_SPOTIFY_LAST_PUBLISH_KEY = "newest_spotify_last_publish"
NEWEST_SPOTIFY_GENERATE_JOB_KEY = "neueste_spotify_generate_job_v1"

# Short HTTP reruns while a background worker talks to Spotify (proxy timeout).
_SPOTIFY_JOB_POLL_INTERVAL_SECONDS = 1.0

# Spotify iframe height and Streamlit ``components.html`` viewport (must match).
_NEWEST_SPOTIFY_PLAYLIST_EMBED_HEIGHT_PX = 720

# Discrete taste-orientation steps for the select slider (German UI labels).
_SPOTIFY_TASTE_ORIENTATION_OPTIONS: tuple[str, ...] = (
    "gar nicht",
    "etwas",
    "mittel",
    "stark",
)
_SPOTIFY_TASTE_ORIENTATION_EXPONENT: dict[str, float] = {
    "gar nicht": 1.0,
    "etwas": 1.0,
    "mittel": 2.0,
    "stark": 3.0,
}

_LOGGER = logging.getLogger(__name__)


def _german_spotify_generate_button_label(
    *,
    can_publish: bool,
    seconds_remaining: int,
    now_utc: datetime,
) -> str:
    """Generate-button label; when rate-limited, appends next allowed local time."""
    base = "Spotify-Playlist erzeugen"
    if can_publish or seconds_remaining <= 0:
        return base
    unlock_at = now_utc + timedelta(seconds=seconds_remaining)
    clock = unlock_at.astimezone().strftime("%H:%M")
    return f"{base} (um {clock} Uhr erneut)"


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
    return read_spotify_token_from_session()


def _ensure_valid_spotify_token(
    client: SpotifyClient,
    token: SpotifyToken,
) -> SpotifyToken:
    """Return a usable token and refresh it when required."""
    if not token.is_expired():
        return token
    if not token.refresh_token:
        raise RuntimeError(
            "Die Spotify-Sitzung ist abgelaufen. Bitte erneut "
            "„Verbindung mit Spotify herstellen“ wählen."
        )
    refreshed = client.refresh_access_token(refresh_token=token.refresh_token)
    persist_spotify_token(refreshed)
    return refreshed


def _token_declares_spotify_scope(token: SpotifyToken, scope: str) -> bool:
    """Return True if the granted scope string from Spotify lists ``scope``."""
    granted = {s for s in (token.scope or "").split() if s}
    return scope in granted


def _render_last_spotify_publish_if_any() -> None:
    """Show embed for the last successfully published playlist."""
    raw = st.session_state.get(NEWEST_SPOTIFY_LAST_PUBLISH_KEY)
    if not isinstance(raw, dict):
        return
    pid_any = raw.get("playlist_id")
    if not isinstance(pid_any, str) or not pid_any.strip():
        return
    pid = pid_any.strip()
    embed_src = f"https://open.spotify.com/embed/playlist/{pid}"
    h = _NEWEST_SPOTIFY_PLAYLIST_EMBED_HEIGHT_PX
    # Streamlit ``height`` is the component iframe viewport; if it is smaller than
    # the inner Spotify iframe, the playlist embed appears clipped.
    components.html(
        (
            f'<iframe title="Spotify" style="border-radius:12px" '
            f'src="{embed_src}?utm_source=generator" width="100%" height="{h}" '
            'frameBorder="0" allowfullscreen="" '
            'allow="autoplay; clipboard-write; encrypted-media; fullscreen; '
            'picture-in-picture" loading="lazy"></iframe>'
        ),
        height=h,
    )


def _run_neueste_spotify_job_worker(
    holder: dict[str, Any],
    *,
    client: SpotifyClient,
    token: SpotifyToken,
    chosen_reviews: list[Review],
    alloc_weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    resolved_playlist_name: str,
    public: bool,
) -> None:
    """Run Spotify API work off the main Streamlit script thread."""
    try:
        outcome = run_neueste_spotify_publish_pipeline(
            client=client,
            token=token,
            chosen_reviews=chosen_reviews,
            alloc_weights=alloc_weights,
            raw_scores=raw_scores,
            target_count=target_count,
            rng=rng,
            resolved_playlist_name=resolved_playlist_name,
            public=public,
        )
        holder["outcome"] = outcome
    except Exception as exc:
        holder["worker_error"] = repr(exc)
    finally:
        holder["done"] = True


def _apply_spotify_generate_job_holder(
    holder: dict[str, Any],
    *,
    profiles_dir: Path,
) -> None:
    """Apply a finished job to session state and show German UI messages."""
    worker_err = holder.get("worker_error")
    if isinstance(worker_err, str) and worker_err:
        st.error("Spotify-Playlist konnte nicht erzeugt werden (unerwarteter Fehler).")
        st.caption(f"Technische Details: {worker_err}")
        return

    outcome_any = holder.get("outcome")
    if not isinstance(outcome_any, NeuesteSpotifyGenerateOutcome):
        st.error(
            "Spotify-Playlist konnte nicht erzeugt werden "
            "(kein Ergebnis vom Hintergrundjob)."
        )
        return

    outcome = outcome_any
    if outcome.unexpected_error:
        st.error("Spotify-Playlist konnte nicht erzeugt werden (unerwarteter Fehler).")
        st.caption(f"Technische Details: {outcome.unexpected_error}")
        return

    if outcome.warn_partial_candidates:
        st.warning(outcome.warn_partial_candidates)

    if outcome.error_no_candidates:
        st.error(
            "Keine Spotify-Treffer für die Auswahl. Bitte Einstellungen "
            "oder den Rezensionen-Pool prüfen."
        )
        return

    if outcome.error_value_message is not None:
        st.error(outcome.error_value_message)
        return

    if outcome.error_runtime_message is not None:
        st.error(
            "Spotify-Playlist konnte nicht erzeugt werden. "
            "Bitte Verbindung und Berechtigungen prüfen."
        )
        st.caption(f"Technische Details: {outcome.error_runtime_message}")
        if outcome.show_runtime_403_caption:
            st.caption(
                "Hinweis: HTTP 403 bedeutet oft fehlende "
                "OAuth-Berechtigungen: private Playlists brauchen "
                "„playlist-modify-private“, öffentliche "
                "„playlist-modify-public“. Zum Auflisten eigener "
                "Playlists (Namensabgleich) braucht Spotify "
                "„playlist-read-private“. Unter „Spotify-App verwalten“ "
                "Zugangsdaten entfernen, `.env`/`SPOTIFY_SCOPES` prüfen, "
                "erneut „Verbindung mit Spotify herstellen“."
            )
        return

    if outcome.publish_succeeded:
        record_spotify_preview_generated(
            session=st.session_state,
            profiles_dir=profiles_dir,
            when_utc=datetime.now(UTC),
        )
        st.session_state[NEWEST_SPOTIFY_LAST_PUBLISH_KEY] = {
            "playlist_id": outcome.playlist_id,
            "external_url": outcome.external_url,
            "created": outcome.created,
        }
        _LOGGER.info(
            "newest spotify publish: done playlist_id=%s created=%s url=%r",
            outcome.playlist_id,
            outcome.created,
            outcome.external_url,
        )
        if not outcome.created:
            st.success(
                "Eine bestehende Playlist gleichen Namens wurde "
                "aktualisiert (Songs ersetzt)."
            )


def render_neueste_spotify_playlist_section(
    *,
    reviews: list[Review],
) -> None:
    """Build a random playlist from the same pool as Neueste Rezensionen."""
    configure_spotify_playlist_logging_from_env()
    st.session_state.pop("newest_spotify_preview", None)
    if not reviews:
        st.info("Keine Rezensionen verfügbar.")
        return

    max_pool = len(reviews)
    target_count = st.slider(
        "Wie viele Songs sollen auf der Playlist stehen?",
        min_value=5,
        max_value=50,
        value=min(30, max(5, max_pool)),
        step=1,
        key="newest-spotify-song-count",
    )
    taste_orientation = st.select_slider(
        "Wie stark soll sich die Playlist an deinem persönlichen Geschmack "
        "orientieren?",
        options=list(_SPOTIFY_TASTE_ORIENTATION_OPTIONS),
        value="etwas",
        key="newest-spotify-taste-orientation",
    )
    if NEWEST_SPOTIFY_PLAYLIST_NAME_KEY not in st.session_state:
        st.session_state[NEWEST_SPOTIFY_PLAYLIST_NAME_KEY] = (
            _default_newest_spotify_playlist_name()
        )
    col_playlist_name, col_playlist_public = st.columns([2, 1], gap="medium")
    with col_playlist_name:
        playlist_name = st.text_input(
            "Name der Spotify-Playlist",
            key=NEWEST_SPOTIFY_PLAYLIST_NAME_KEY,
        )
    with col_playlist_public:
        # Offset so the checkbox aligns with the text field (label sits above input).
        st.markdown(
            '<div style="min-height: 2.5rem;" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        make_playlist_public = st.checkbox(
            "Playlist öffentlich machen",
            value=False,
            key="newest-spotify-playlist-public",
        )

    cfg = _try_load_user_spotify_config()
    if cfg is None:
        try:
            cfg = SpotifyAuthConfig.from_env()
        except SpotifyConfigError as exc:
            st.error(f"Spotify-Konfiguration fehlt: {exc}")
            return
    client = SpotifyClient(cfg)

    token = _stored_spotify_token()

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
    can_publish_playlist = cooldown_remaining == 0

    st.markdown(
        '<div style="min-height: 2.5rem;" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    if token is None:
        render_spotify_login_link_under_preview(client)
        generate_clicked = False
    else:
        generate_clicked = st.button(
            _german_spotify_generate_button_label(
                can_publish=can_publish_playlist,
                seconds_remaining=cooldown_remaining,
                now_utc=now_utc,
            ),
            type="primary",
            key="newest-spotify-generate",
            width="stretch",
            disabled=not can_publish_playlist,
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
            "oft mit 403 Forbidden. Bitte unter „Spotify-App verwalten“ die "
            "Zugangsdaten entfernen und erneut „Verbindung mit Spotify "
            "herstellen“, und in der `.env` sicherstellen, dass "
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
            "„playlist-modify-public“. Bitte unter „Spotify-App verwalten“ die "
            "Zugangsdaten entfernen und erneut verbinden, oder `SPOTIFY_SCOPES` "
            "in der `.env` prüfen."
        )
    if scope_check_token is not None and not _token_declares_spotify_scope(
        scope_check_token,
        "playlist-read-private",
    ):
        st.warning(
            "Zum Prüfen bestehender Playlists gleichen Namens braucht Spotify das "
            "Scope „playlist-read-private“. Ohne dieses Recht schlägt die API bei "
            "„Spotify-Playlist erzeugen“ oft mit 403 (Insufficient client scope) "
            "fehl. Bitte unter „Spotify-App verwalten“ die Zugangsdaten entfernen "
            "und erneut verbinden, und in der `.env` sicherstellen, dass "
            "`SPOTIFY_SCOPES` dieses Scope enthält."
        )

    if generate_clicked and can_publish_playlist:
        existing_job = st.session_state.get(NEWEST_SPOTIFY_GENERATE_JOB_KEY)
        prev_holder = (
            existing_job.get("holder") if isinstance(existing_job, dict) else None
        )
        if isinstance(prev_holder, dict) and not prev_holder.get("done"):
            st.warning("Eine Playlist-Erstellung läuft bereits. Bitte kurz warten.")
        else:
            ranked_rows = (
                None
                if taste_orientation == "gar nicht"
                else preference_rank_rows_for_reviews(reviews)
            )
            chosen_reviews, weights, raw_scores = build_album_weights(
                reviews,
                ranked_rows,
            )
            taste_exponent = _SPOTIFY_TASTE_ORIENTATION_EXPONENT[taste_orientation]
            _LOGGER.info(
                "newest spotify playlist section: n_chosen_albums=%s "
                "ranked_rows_available=%s target_songs=%s taste_orientation=%s "
                "taste_exponent=%s",
                len(chosen_reviews),
                ranked_rows is not None,
                target_count,
                taste_orientation,
                taste_exponent,
            )
            _log_weight_summary(
                weights,
                review_ids=[int(r.id) for r in chosen_reviews],
            )
            rng = random.Random(secrets.randbits(64))
            alloc_weights = amplify_preference_weights(
                weights,
                exponent=taste_exponent,
            )
            token_for_publish = _ensure_valid_spotify_token(client, token)
            resolved_name = (
                playlist_name.strip() or _default_newest_spotify_playlist_name()
            )
            holder: dict[str, Any] = {
                "done": False,
                "outcome": None,
                "worker_error": None,
            }
            thread = threading.Thread(
                target=_run_neueste_spotify_job_worker,
                kwargs={
                    "holder": holder,
                    "client": client,
                    "token": token_for_publish,
                    "chosen_reviews": chosen_reviews,
                    "alloc_weights": alloc_weights,
                    "raw_scores": raw_scores,
                    "target_count": target_count,
                    "rng": rng,
                    "resolved_playlist_name": resolved_name,
                    "public": make_playlist_public,
                },
                daemon=True,
            )
            st.session_state[NEWEST_SPOTIFY_GENERATE_JOB_KEY] = {
                "holder": holder,
                "thread": thread,
            }
            thread.start()
            _LOGGER.info(
                "newest spotify publish: background job started "
                "n_albums=%s target_count=%s",
                len(chosen_reviews),
                target_count,
            )

    _render_last_spotify_publish_if_any()

    job = st.session_state.get(NEWEST_SPOTIFY_GENERATE_JOB_KEY)
    if isinstance(job, dict):
        holder_poll = job.get("holder")
        if not isinstance(holder_poll, dict):
            del st.session_state[NEWEST_SPOTIFY_GENERATE_JOB_KEY]
        elif holder_poll["done"]:
            _apply_spotify_generate_job_holder(
                holder_poll,
                profiles_dir=profiles_dir,
            )
            del st.session_state[NEWEST_SPOTIFY_GENERATE_JOB_KEY]
            st.rerun()
        else:
            st.info("Die Playlist wird erzeugt - das kann einige Sekunden dauern.")
            time.sleep(_SPOTIFY_JOB_POLL_INTERVAL_SECONDS)
            st.rerun()
