"""Streamlit dashboard background image helpers (CSS injection)."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import streamlit as st

from music_review.config import get_project_root

logger = logging.getLogger(__name__)

DEFAULT_DASHBOARD_BACKGROUND_RELATIVE = Path("assets/plattenradar_background.png")


def dashboard_background_png_path() -> Path:
    """Return the default dashboard background PNG path under the project root."""
    return get_project_root() / DEFAULT_DASHBOARD_BACKGROUND_RELATIVE


def png_bytes_to_data_url(png_bytes: bytes) -> str:
    """Return a PNG ``data:`` URL suitable for embedding in CSS ``url(...)``."""
    encoded = base64.standard_b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_streamlit_app_background_css(data_url: str) -> str:
    """Build CSS for a full-viewport background on Streamlit's ``.stApp`` shell."""
    return f"""
        <style>
        .stApp {{
            background-image: url("{data_url}");
            background-size: cover;
            background-position: center center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        </style>
        """


def inject_streamlit_app_background_image(path: Path | None = None) -> bool:
    """Inject a PNG background for the Streamlit app shell.

    Returns True when CSS was injected, False when the file is missing or unreadable.
    """
    resolved = dashboard_background_png_path() if path is None else path
    if not resolved.is_file():
        logger.warning("Dashboard background PNG not found at %s; skipping.", resolved)
        return False
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        logger.warning(
            "Dashboard background PNG could not be read from %s: %s",
            resolved,
            exc,
        )
        return False

    data_url = png_bytes_to_data_url(raw)
    st.markdown(build_streamlit_app_background_css(data_url), unsafe_allow_html=True)
    logger.info("Injected Streamlit dashboard background from %s", resolved)
    return True
