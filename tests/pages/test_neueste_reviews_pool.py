from __future__ import annotations

import importlib
import logging

import pytest


def test_neueste_reviews_pool_importable() -> None:
    module = importlib.import_module("pages.neueste_reviews_pool")
    assert hasattr(module, "fetch_newest_reviews_pool")
    assert hasattr(module, "ensure_neueste_session_defaults")
    assert hasattr(module, "RECENT_DEFAULT")


def _reset_spotify_playlist_loggers(module: object) -> None:
    names = getattr(module, "_SPOTIFY_PLAYLIST_LOG_TARGET_NAMES", ())
    for name in names:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
        lg.setLevel(logging.WARNING)


def test_configure_spotify_playlist_logging_skips_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.neueste_reviews_pool")
    monkeypatch.delenv("MUSIC_REVIEW_SPOTIFY_PLAYLIST_LOG", raising=False)
    module._spotify_playlist_log_configured = False
    _reset_spotify_playlist_loggers(module)
    lg = logging.getLogger("pages.neueste_reviews_pool")
    before = len(lg.handlers)
    module.configure_spotify_playlist_logging_from_env()
    assert len(lg.handlers) == before


def test_configure_spotify_playlist_logging_from_env_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module("pages.neueste_reviews_pool")
    monkeypatch.setenv("MUSIC_REVIEW_SPOTIFY_PLAYLIST_LOG", "info")
    module._spotify_playlist_log_configured = False
    _reset_spotify_playlist_loggers(module)
    try:
        module.configure_spotify_playlist_logging_from_env()
        lg = logging.getLogger("pages.neueste_reviews_pool")
        n_handlers = len(lg.handlers)
        assert n_handlers >= 1
        module.configure_spotify_playlist_logging_from_env()
        assert len(lg.handlers) == n_handlers
    finally:
        module._spotify_playlist_log_configured = False
        _reset_spotify_playlist_loggers(module)
        monkeypatch.delenv("MUSIC_REVIEW_SPOTIFY_PLAYLIST_LOG", raising=False)
