"""Smoke tests for the logged-in konto panel module."""

from __future__ import annotations

from pages.konto_session_panel import (
    KEY_KONTO_SIGN_OUT,
    KEY_WEITER,
    render_logged_in_konto_panel,
)


def test_konto_session_panel_defines_stable_widget_keys() -> None:
    """Widget keys must stay stable so Streamlit session state survives reruns."""
    assert KEY_KONTO_SIGN_OUT == "konto_panel_sign_out"
    assert KEY_WEITER == "konto_panel_weiter"
    assert callable(render_logged_in_konto_panel)
