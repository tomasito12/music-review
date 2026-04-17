"""Streamlit shell branding (navigation logo)."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

from music_review.config import get_project_root
from music_review.dashboard.logo_ui_image import (
    rgba_png_bytes_with_near_black_knocked_out,
)
from music_review.dashboard.streamlit_background import (
    inject_streamlit_app_background_image,
)

logger = logging.getLogger(__name__)

DEFAULT_DASHBOARD_LOGO_RELATIVE = Path("assets/plattenradar_logo.png")

# ``st.logo`` uses fixed theme heights on the ``img`` itself. The logo ``img``
# carries ``data-testid="stLogo"`` (main) or ``stSidebarLogo`` (sidebar), not a
# nested ``img`` child — target those elements directly.
LOGO_SHELL_IMAGE_MAX_HEIGHT_PX = 132
# Bump when logo processing changes so ``st.cache_data`` does not serve stale PNGs.
LOGO_UI_PROCESSING_VERSION: int = 5


@st.cache_data(show_spinner=False)
def _cached_logo_ui_png_bytes(
    logo_path: str,
    mtime_ns: int,
    processing_version: int,
) -> bytes:
    """Process logo once per path + mtime + processing recipe."""
    _ = mtime_ns
    _ = processing_version
    raw = Path(logo_path).read_bytes()
    return rgba_png_bytes_with_near_black_knocked_out(raw)


def build_dashboard_logo_shell_css() -> str:
    """Return CSS for a larger logo and a light frame around dark artwork."""
    h = int(LOGO_SHELL_IMAGE_MAX_HEIGHT_PX)
    return f"""
        <style>
        /* Home navigation hit area (main + sidebar). */
        [data-testid="stLogoLink"] {{
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.98) 0%,
                rgba(241, 245, 249, 0.98) 100%
            ) !important;
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            border-radius: 14px !important;
            padding: 10px 14px !important;
            box-shadow: none !important;
        }}
        /* The logo is the ``img`` with the test id (no nested ``img``). */
        img[data-testid="stLogo"],
        img[data-testid="stSidebarLogo"] {{
            height: auto !important;
            max-height: {h}px !important;
            width: auto !important;
            max-width: min(280px, 40vw) !important;
            object-fit: contain !important;
            object-position: center !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            outline: none !important;
        }}
        </style>
        """


def inject_dashboard_logo_shell_css() -> None:
    """Inject CSS overrides for ``st.logo`` (size and light backdrop)."""
    st.markdown(
        build_dashboard_logo_shell_css(),
        unsafe_allow_html=True,
    )


def dashboard_logo_png_path() -> Path:
    """Return the default dashboard logo PNG path under the project root."""
    return get_project_root() / DEFAULT_DASHBOARD_LOGO_RELATIVE


def read_processed_dashboard_logo_bytes() -> bytes | None:
    """Return shell-processed PNG bytes for inline HTML, or None if unavailable."""
    path = dashboard_logo_png_path()
    if not path.is_file():
        return None
    try:
        path_str = str(path.resolve())
        mtime_ns = int(path.stat().st_mtime_ns)
        return _cached_logo_ui_png_bytes(
            path_str,
            mtime_ns,
            LOGO_UI_PROCESSING_VERSION,
        )
    except (OSError, ValueError, UnidentifiedImageError):
        logger.debug("Inline logo bytes unavailable", exc_info=True)
        return None


def welcome_start_title_inner_html(processed_png_bytes: bytes | None) -> str:
    """Return HTML for the start-page title row (logo image or text fallback)."""
    if processed_png_bytes is None:
        return '<p class="welcome-title">Plattenradar</p>'
    encoded = base64.standard_b64encode(processed_png_bytes).decode("ascii")
    return (
        '<p class="welcome-logo" role="img" aria-label="Plattenradar">'
        f'<img class="welcome-title-img" src="data:image/png;base64,{encoded}" '
        'alt="Plattenradar" />'
        "</p>"
    )


def ensure_plattenradar_dashboard_chrome() -> None:
    """Apply background and navigation logo on every script run.

    With ``st.navigation``, file-based pages execute without re-running the
    entrypoint ``main()``; call this from each page (or a shared hook such as
    ``render_toolbar``) so the shell stays consistent.
    """
    inject_streamlit_app_background_image()
    inject_plattenradar_navigation_logo()
    inject_dashboard_logo_shell_css()


def inject_plattenradar_navigation_logo(path: Path | None = None) -> bool:
    """Show a square logo in the upper-left; click returns to the app home page.

    Uses ``st.logo`` (Streamlit ``>=1.50``). When the file is missing, does nothing.
    """
    resolved = dashboard_logo_png_path() if path is None else path
    if not resolved.is_file():
        logger.info("Dashboard logo PNG not found at %s; skipping st.logo.", resolved)
        return False
    path_str = str(resolved.resolve())
    try:
        mtime_ns = int(resolved.stat().st_mtime_ns)
        processed = _cached_logo_ui_png_bytes(
            path_str,
            mtime_ns,
            LOGO_UI_PROCESSING_VERSION,
        )
        st.logo(Image.open(io.BytesIO(processed)).convert("RGBA"), size="large")
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        logger.warning("Logo UI processing failed; using raw file (%s)", exc)
        st.logo(path_str, size="large")
    logger.info("Rendered Streamlit navigation logo from %s", resolved)
    return True
