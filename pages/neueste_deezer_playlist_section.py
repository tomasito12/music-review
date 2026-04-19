"""Deezer playlist builder UI for newest reviews and the album archive.

Mirror of :mod:`pages.neueste_spotify_playlist_section`. Both modes share the
same controls (song count, taste orientation, playlist name, public toggle)
and the same generator pipeline. The differences are the candidate pool
(newest reviews vs. recommendations) and the per-mode widget keys, which are
isolated via a ``key_prefix`` so Streamlit keeps state per tab.

Deezer is simpler than Spotify in two relevant ways:
* No PKCE OAuth dance; only a CSRF state cookie is needed.
* Tokens granted with ``offline_access`` do not expire and need no refresh,
  so this section never tries to refresh a token before publishing.
"""

from __future__ import annotations

import logging
import random
import secrets
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from pages.deezer_connection_ui import (
    render_deezer_login_link_for_playlist_hub,
    resolve_deezer_auth_config,
)
from pages.deezer_token_persist import read_deezer_token_from_session
from pages.neueste_reviews_pool import (
    configure_spotify_playlist_logging_from_env,
    preference_rank_rows_for_reviews,
)
from pages.recommendations_pool import archive_playlist_candidates

from music_review.dashboard.neueste_deezer_generate_job import (
    NeuesteDeezerGenerateOutcome,
    run_neueste_deezer_publish_pipeline,
)
from music_review.dashboard.newest_spotify_playlist import (
    SelectionStrategy,
    amplify_preference_weights,
    build_album_weights,
)
from music_review.dashboard.user_profile_store import (
    deezer_preview_cooldown_seconds_remaining,
    default_profiles_dir,
    get_deezer_preview_last_generated_at,
    record_deezer_preview_generated,
)
from music_review.domain.models import Review
from music_review.integrations.deezer_client import DeezerClient, DeezerToken

NEWEST_DEEZER_PLAYLIST_NAME_KEY = "newest-deezer-playlist-name"
NEWEST_DEEZER_LAST_PUBLISH_KEY = "newest_deezer_last_publish"
NEWEST_DEEZER_GENERATE_JOB_KEY = "neueste_deezer_generate_job_v1"

_DEEZER_JOB_POLL_INTERVAL_SECONDS = 1.0
_NEWEST_DEEZER_PLAYLIST_EMBED_HEIGHT_PX = 720

_DEEZER_TASTE_ORIENTATION_OPTIONS: tuple[str, ...] = (
    "gar nicht",
    "etwas",
    "mittel",
    "stark",
)
_DEEZER_TASTE_ORIENTATION_EXPONENT: dict[str, float] = {
    "gar nicht": 1.0,
    "etwas": 1.0,
    "mittel": 2.0,
    "stark": 3.0,
}

_LOGGER = logging.getLogger(__name__)


def _german_deezer_generate_button_label(
    *,
    can_publish: bool,
    seconds_remaining: int,
    now_utc: datetime,
) -> str:
    """Generate-button label; appends next allowed local time when rate-limited."""
    base = "Deezer-Playlist erzeugen"
    if can_publish or seconds_remaining <= 0:
        return base
    unlock_at = now_utc + timedelta(seconds=seconds_remaining)
    clock = unlock_at.astimezone().strftime("%H:%M")
    return f"{base} (um {clock} Uhr erneut)"


def _default_newest_deezer_playlist_name() -> str:
    """Default Deezer playlist label: Plattenradar YYYY-MM-DD (local date)."""
    return f"Plattenradar {date.today().isoformat()}"


def _stored_deezer_token() -> DeezerToken | None:
    return read_deezer_token_from_session()


def _render_last_deezer_publish_if_any() -> None:
    """Show embed for the last successfully published Deezer playlist."""
    raw = st.session_state.get(NEWEST_DEEZER_LAST_PUBLISH_KEY)
    if not isinstance(raw, dict):
        return
    pid_any = raw.get("playlist_id")
    if not isinstance(pid_any, str) or not pid_any.strip():
        return
    pid = pid_any.strip()
    embed_src = f"https://widget.deezer.com/widget/dark/playlist/{pid}"
    h = _NEWEST_DEEZER_PLAYLIST_EMBED_HEIGHT_PX
    components.html(
        (
            f'<iframe title="Deezer" style="border-radius:12px" '
            f'src="{embed_src}" width="100%" height="{h}" '
            'frameBorder="0" allowfullscreen="" '
            'allow="encrypted-media; clipboard-write" loading="lazy"></iframe>'
        ),
        height=h,
    )


def _run_neueste_deezer_job_worker(
    holder: dict[str, Any],
    *,
    client: DeezerClient,
    token: DeezerToken,
    chosen_reviews: list[Review],
    alloc_weights: list[float],
    raw_scores: list[float],
    target_count: int,
    rng: random.Random,
    resolved_playlist_name: str,
    public: bool,
    selection_strategy: SelectionStrategy,
) -> None:
    """Run Deezer API work off the main Streamlit script thread."""
    try:
        outcome = run_neueste_deezer_publish_pipeline(
            client=client,
            token=token,
            chosen_reviews=chosen_reviews,
            alloc_weights=alloc_weights,
            raw_scores=raw_scores,
            target_count=target_count,
            rng=rng,
            resolved_playlist_name=resolved_playlist_name,
            public=public,
            selection_strategy=selection_strategy,
        )
        holder["outcome"] = outcome
    except Exception as exc:
        holder["worker_error"] = repr(exc)
    finally:
        holder["done"] = True


def _apply_deezer_generate_job_holder(
    holder: dict[str, Any],
    *,
    profiles_dir: Path,
) -> None:
    """Apply a finished job to session state and show German UI messages."""
    worker_err = holder.get("worker_error")
    if isinstance(worker_err, str) and worker_err:
        st.error("Deezer-Playlist konnte nicht erzeugt werden (unerwarteter Fehler).")
        st.caption(f"Technische Details: {worker_err}")
        return

    outcome_any = holder.get("outcome")
    if not isinstance(outcome_any, NeuesteDeezerGenerateOutcome):
        st.error(
            "Deezer-Playlist konnte nicht erzeugt werden "
            "(kein Ergebnis vom Hintergrundjob)."
        )
        return

    outcome = outcome_any
    if outcome.unexpected_error:
        st.error("Deezer-Playlist konnte nicht erzeugt werden (unerwarteter Fehler).")
        st.caption(f"Technische Details: {outcome.unexpected_error}")
        return

    if outcome.warn_partial_candidates:
        st.warning(outcome.warn_partial_candidates)

    if outcome.error_no_candidates:
        st.error(
            "Keine Deezer-Treffer für die Auswahl. Bitte Einstellungen "
            "oder den Rezensionen-Pool prüfen."
        )
        return

    if outcome.error_value_message is not None:
        st.error(outcome.error_value_message)
        return

    if outcome.error_runtime_message is not None:
        st.error(
            "Deezer-Playlist konnte nicht erzeugt werden. "
            "Bitte Verbindung und Berechtigungen prüfen."
        )
        st.caption(f"Technische Details: {outcome.error_runtime_message}")
        return

    if outcome.publish_succeeded:
        record_deezer_preview_generated(
            session=st.session_state,
            profiles_dir=profiles_dir,
            when_utc=datetime.now(UTC),
        )
        st.session_state[NEWEST_DEEZER_LAST_PUBLISH_KEY] = {
            "playlist_id": outcome.playlist_id,
            "external_url": outcome.external_url,
            "created": outcome.created,
        }
        _LOGGER.info(
            "newest deezer publish: done playlist_id=%s created=%s url=%r",
            outcome.playlist_id,
            outcome.created,
            outcome.external_url,
        )
        if not outcome.created:
            st.success(
                "Eine bestehende Playlist gleichen Namens wurde "
                "aktualisiert (Songs ersetzt)."
            )


def _start_deezer_generate_job(
    *,
    client: DeezerClient,
    token: DeezerToken,
    reviews: list[Review],
    ranked_rows: list[dict[str, Any]] | None,
    target_count: int,
    taste_orientation: str,
    playlist_name: str,
    make_playlist_public: bool,
    log_label: str,
    selection_strategy: SelectionStrategy,
) -> bool:
    """Compute weights and kick off the background publish thread.

    Always returns ``True``: unlike Spotify, Deezer tokens granted with
    ``offline_access`` do not expire and require no pre-flight refresh.
    """
    chosen_reviews, weights, raw_scores = build_album_weights(reviews, ranked_rows)
    taste_exponent = _DEEZER_TASTE_ORIENTATION_EXPONENT[taste_orientation]
    _LOGGER.info(
        "%s playlist section: n_chosen_albums=%s ranked_rows_available=%s "
        "target_songs=%s taste_orientation=%s taste_exponent=%s strategy=%s",
        log_label,
        len(chosen_reviews),
        ranked_rows is not None,
        target_count,
        taste_orientation,
        taste_exponent,
        selection_strategy,
    )
    rng = random.Random(secrets.randbits(64))
    alloc_weights = amplify_preference_weights(weights, exponent=taste_exponent)
    resolved_name = playlist_name.strip() or _default_newest_deezer_playlist_name()
    holder: dict[str, Any] = {
        "done": False,
        "outcome": None,
        "worker_error": None,
    }
    thread = threading.Thread(
        target=_run_neueste_deezer_job_worker,
        kwargs={
            "holder": holder,
            "client": client,
            "token": token,
            "chosen_reviews": chosen_reviews,
            "alloc_weights": alloc_weights,
            "raw_scores": raw_scores,
            "target_count": target_count,
            "rng": rng,
            "resolved_playlist_name": resolved_name,
            "public": make_playlist_public,
            "selection_strategy": selection_strategy,
        },
        daemon=True,
    )
    st.session_state[NEWEST_DEEZER_GENERATE_JOB_KEY] = {
        "holder": holder,
        "thread": thread,
    }
    thread.start()
    _LOGGER.info(
        "%s publish: background job started n_albums=%s target_count=%s",
        log_label,
        len(chosen_reviews),
        target_count,
    )
    return True


def _render_playlist_controls_and_generate(
    *,
    reviews: list[Review],
    resolve_ranked_rows: Callable[[str], list[dict[str, Any]] | None],
    key_prefix: str,
    default_song_count: int,
    pool_size_for_log: int,
    log_label: str,
    selection_strategy: SelectionStrategy,
) -> None:
    """Render the shared Deezer playlist UI for one mode."""
    name_key = f"{key_prefix}-deezer-playlist-name"
    target_count_key = f"{key_prefix}-deezer-song-count"
    taste_key = f"{key_prefix}-deezer-taste-orientation"
    public_key = f"{key_prefix}-deezer-playlist-public"
    generate_key = f"{key_prefix}-deezer-generate"

    target_count = st.slider(
        "Wie viele Songs sollen auf der Playlist stehen?",
        min_value=5,
        max_value=50,
        value=default_song_count,
        step=1,
        key=target_count_key,
    )
    taste_orientation = st.select_slider(
        "Wie stark soll sich die Playlist an deinem persönlichen Geschmack "
        "orientieren?",
        options=list(_DEEZER_TASTE_ORIENTATION_OPTIONS),
        value="etwas",
        key=taste_key,
    )
    if name_key not in st.session_state:
        st.session_state[name_key] = _default_newest_deezer_playlist_name()
    col_playlist_name, col_playlist_public = st.columns([2, 1], gap="medium")
    with col_playlist_name:
        playlist_name = st.text_input(
            "Name der Deezer-Playlist",
            key=name_key,
        )
    with col_playlist_public:
        st.markdown(
            '<div style="min-height: 2.5rem;" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        make_playlist_public = st.checkbox(
            "Playlist öffentlich machen",
            value=False,
            key=public_key,
        )

    cfg = resolve_deezer_auth_config()
    if cfg is None:
        st.error(
            "Deezer-Konfiguration fehlt: bitte `DEEZER_APP_ID`, `DEEZER_APP_SECRET` "
            "und `DEEZER_REDIRECT_URI` in `.env` setzen oder eigene "
            "Zugangsdaten unter „Streaming-Verbindungen“ hinterlegen."
        )
        return
    client = DeezerClient(cfg)

    token = _stored_deezer_token()

    profiles_dir = default_profiles_dir()
    now_utc = datetime.now(UTC)
    last_preview_at = get_deezer_preview_last_generated_at(
        session=st.session_state,
        profiles_dir=profiles_dir,
    )
    cooldown_remaining = deezer_preview_cooldown_seconds_remaining(
        now_utc=now_utc,
        last_generated_at_utc=last_preview_at,
    )
    can_publish_playlist = cooldown_remaining == 0

    st.markdown(
        '<div style="min-height: 2.5rem;" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    if token is None:
        render_deezer_login_link_for_playlist_hub(client)
        generate_clicked = False
    else:
        generate_clicked = st.button(
            _german_deezer_generate_button_label(
                can_publish=can_publish_playlist,
                seconds_remaining=cooldown_remaining,
                now_utc=now_utc,
            ),
            type="primary",
            key=generate_key,
            width="stretch",
            disabled=not can_publish_playlist,
        )

    if generate_clicked and can_publish_playlist and token is not None:
        existing_job = st.session_state.get(NEWEST_DEEZER_GENERATE_JOB_KEY)
        prev_holder = (
            existing_job.get("holder") if isinstance(existing_job, dict) else None
        )
        if isinstance(prev_holder, dict) and not prev_holder.get("done"):
            st.warning("Eine Playlist-Erstellung läuft bereits. Bitte kurz warten.")
        else:
            ranked_rows = resolve_ranked_rows(taste_orientation)
            _LOGGER.debug(
                "%s playlist section: pool_size=%s",
                log_label,
                pool_size_for_log,
            )
            _start_deezer_generate_job(
                client=client,
                token=token,
                reviews=reviews,
                ranked_rows=ranked_rows,
                target_count=target_count,
                taste_orientation=taste_orientation,
                playlist_name=playlist_name,
                make_playlist_public=make_playlist_public,
                log_label=log_label,
                selection_strategy=selection_strategy,
            )

    _render_last_deezer_publish_if_any()

    job = st.session_state.get(NEWEST_DEEZER_GENERATE_JOB_KEY)
    if isinstance(job, dict):
        holder_poll = job.get("holder")
        if not isinstance(holder_poll, dict):
            del st.session_state[NEWEST_DEEZER_GENERATE_JOB_KEY]
        elif holder_poll["done"]:
            _apply_deezer_generate_job_holder(
                holder_poll,
                profiles_dir=profiles_dir,
            )
            del st.session_state[NEWEST_DEEZER_GENERATE_JOB_KEY]
            st.rerun()
        else:
            st.info("Die Playlist wird erzeugt - das kann einige Sekunden dauern.")
            time.sleep(_DEEZER_JOB_POLL_INTERVAL_SECONDS)
            st.rerun()


def render_neueste_deezer_playlist_section(
    *,
    reviews: list[Review],
) -> None:
    """Build a random Deezer playlist from the newest reviews pool."""
    configure_spotify_playlist_logging_from_env()
    st.session_state.pop("newest_deezer_preview", None)
    if not reviews:
        st.info("Keine Rezensionen verfügbar.")
        return

    def _resolve_ranked_rows(taste_orientation: str) -> list[dict[str, Any]] | None:
        if taste_orientation == "gar nicht":
            return None
        return preference_rank_rows_for_reviews(reviews)

    _render_playlist_controls_and_generate(
        reviews=reviews,
        resolve_ranked_rows=_resolve_ranked_rows,
        key_prefix="newest",
        default_song_count=min(30, max(5, len(reviews))),
        pool_size_for_log=len(reviews),
        log_label="newest deezer",
        selection_strategy="stratified",
    )


def render_archive_deezer_playlist_section() -> None:
    """Build a random Deezer playlist from the entire scored album archive."""
    configure_spotify_playlist_logging_from_env()
    st.session_state.pop("newest_deezer_preview", None)
    reviews, ranked_rows = archive_playlist_candidates()
    if not reviews or ranked_rows is None:
        st.info(
            "Keine passenden Alben gefunden. Bitte zuerst auf "
            "„Musikpräferenzen ändern“ Stilrichtungen wählen oder Filter "
            "im Filter-Schritt anpassen."
        )
        return

    def _resolve_ranked_rows(_taste_orientation: str) -> list[dict[str, Any]] | None:
        return ranked_rows

    _render_playlist_controls_and_generate(
        reviews=reviews,
        resolve_ranked_rows=_resolve_ranked_rows,
        key_prefix="archive",
        default_song_count=min(30, max(5, len(reviews))),
        pool_size_for_log=len(reviews),
        log_label="archive deezer",
        selection_strategy="weighted_sample",
    )
