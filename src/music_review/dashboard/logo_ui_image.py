"""Raster logo tweaks for light Streamlit shells (e.g. knock out black matting)."""

from __future__ import annotations

import io
from collections import deque
from typing import Final

import numpy as np
from PIL import Image

DEFAULT_LOGO_KNOCKOUT_RGB_THRESHOLD: Final[int] = 50
# After matting removal, anti-alias rings are often dark but nearly gray.
DEFAULT_LOGO_HALO_MAX_CHANNEL: Final[int] = 78
DEFAULT_LOGO_HALO_CHROMA_MAX: Final[int] = 18
# Pixels of padding after auto-crop (keeps anti-alias off the image edge).
DEFAULT_LOGO_TRIM_PAD_PX: Final[int] = 1
# Upscale trimmed art so browser downscaling looks smooth (not tiny bitmap blown up).
DEFAULT_LOGO_RASTER_MIN_LONG_EDGE: Final[int] = 640
# Skip quality upscale for tiny fixtures / degenerate images.
DEFAULT_LOGO_UPSCALE_SKIP_IF_LONGEST_BELOW: Final[int] = 64


def ensure_rgba_longest_edge_at_least(
    image: Image.Image,
    *,
    min_long_edge: int = DEFAULT_LOGO_RASTER_MIN_LONG_EDGE,
    skip_if_longest_below: int = DEFAULT_LOGO_UPSCALE_SKIP_IF_LONGEST_BELOW,
) -> Image.Image:
    """If the image is small, upscale with LANCZOS so UI scaling stays smooth."""
    if min_long_edge < 64 or min_long_edge > 4096:
        msg = "min_long_edge must be between 64 and 4096"
        raise ValueError(msg)
    if skip_if_longest_below < 0 or skip_if_longest_below > 256:
        msg = "skip_if_longest_below must be between 0 and 256"
        raise ValueError(msg)
    im = image.convert("RGBA")
    w, h = im.size
    longest = max(w, h)
    if longest < skip_if_longest_below or longest >= min_long_edge:
        return im
    scale = min_long_edge / float(longest)
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    return im.resize((new_w, new_h), Image.Resampling.LANCZOS)


def trim_rgba_image_to_nontransparent_bbox(
    image: Image.Image,
    *,
    pad_px: int = DEFAULT_LOGO_TRIM_PAD_PX,
) -> Image.Image:
    """Crop an RGBA image to the bounding box of pixels with alpha > 0."""
    if pad_px < 0 or pad_px > 64:
        msg = "pad_px must be between 0 and 64"
        raise ValueError(msg)
    im = image.convert("RGBA")
    arr = np.asarray(im, dtype=np.uint8)
    alpha = arr[:, :, 3]
    row_hit = np.any(alpha > 0, axis=1)
    col_hit = np.any(alpha > 0, axis=0)
    if not np.any(row_hit) or not np.any(col_hit):
        return im
    y_indices = np.flatnonzero(row_hit)
    x_indices = np.flatnonzero(col_hit)
    y0, y1 = int(y_indices[0]), int(y_indices[-1])
    x0, x1 = int(x_indices[0]), int(x_indices[-1])
    height, width = alpha.shape
    pad = int(pad_px)
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(width - 1, x1 + pad)
    y1 = min(height - 1, y1 + pad)
    return im.crop((x0, y0, x1 + 1, y1 + 1))


def _knock_out_low_chroma_dark_pixels(
    arr: np.ndarray,
    *,
    max_channel: int,
    chroma_max: int,
) -> None:
    """Turn dark, low-saturation pixels transparent (edge halos next to black)."""
    rgb = arr[:, :, :3]
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    chroma = mx - mn
    grayish_dark = (mx <= max_channel) & (chroma <= chroma_max)
    alpha = arr[:, :, 3]
    arr[:, :, 3] = np.where(grayish_dark & (alpha > 0), 0, alpha).astype(np.uint8)


def _flood_transparent_light_edge_matte(arr: np.ndarray) -> None:
    """Remove bright, low-chroma padding that touches the image border (in-place)."""
    height, width = int(arr.shape[0]), int(arr.shape[1])
    r0 = arr[:, :, 0].astype(np.int16)
    g0 = arr[:, :, 1].astype(np.int16)
    b0 = arr[:, :, 2].astype(np.int16)
    mx = np.maximum(np.maximum(r0, g0), b0)
    mn = np.minimum(np.minimum(r0, g0), b0)
    chroma = mx - mn

    def seed_ok(y: int, x: int) -> bool:
        if arr[y, x, 3] == 0:
            return False
        return (
            int(arr[y, x, 0]) >= 246
            and int(arr[y, x, 1]) >= 246
            and int(arr[y, x, 2]) >= 246
            and int(chroma[y, x]) <= 12
        )

    def expand_ok(y: int, x: int) -> bool:
        if arr[y, x, 3] == 0:
            return False
        return (
            int(arr[y, x, 0]) >= 240
            and int(arr[y, x, 1]) >= 240
            and int(arr[y, x, 2]) >= 240
            and int(chroma[y, x]) <= 22
        )

    seen = np.zeros((height, width), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(width):
        for y in (0, height - 1):
            if seed_ok(y, x) and not seen[y, x]:
                seen[y, x] = True
                q.append((x, y))
    for y in range(1, height - 1):
        for x in (0, width - 1):
            if seed_ok(y, x) and not seen[y, x]:
                seen[y, x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        arr[y, x, 3] = 0
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if seen[ny, nx] or not expand_ok(ny, nx):
                continue
            seen[ny, nx] = True
            q.append((nx, ny))


def rgba_png_bytes_with_near_black_knocked_out(
    png_bytes: bytes,
    *,
    rgb_threshold: int = DEFAULT_LOGO_KNOCKOUT_RGB_THRESHOLD,
    halo_max_channel: int = DEFAULT_LOGO_HALO_MAX_CHANNEL,
    halo_chroma_max: int = DEFAULT_LOGO_HALO_CHROMA_MAX,
) -> bytes:
    """Return PNG bytes where dark ``RGB`` pixels become fully transparent.

    Pixels with ``R, G, B <= rgb_threshold`` are treated as background matting
    (typical flat ``#000`` blocks around a mark). A second pass removes dark,
    low-chroma pixels (common anti-alias halos) without touching saturated blues.
    """
    if rgb_threshold < 0 or rgb_threshold > 255:
        msg = "rgb_threshold must be between 0 and 255"
        raise ValueError(msg)
    if halo_max_channel < 0 or halo_max_channel > 255:
        msg = "halo_max_channel must be between 0 and 255"
        raise ValueError(msg)
    if halo_chroma_max < 0 or halo_chroma_max > 255:
        msg = "halo_chroma_max must be between 0 and 255"
        raise ValueError(msg)
    try:
        base = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except OSError as exc:
        msg = "Invalid or unreadable raster bytes for logo processing"
        raise ValueError(msg) from exc

    arr = np.asarray(base, dtype=np.uint8).copy()
    rgb = arr[:, :, :3]
    dark = (
        (rgb[:, :, 0] <= rgb_threshold)
        & (rgb[:, :, 1] <= rgb_threshold)
        & (rgb[:, :, 2] <= rgb_threshold)
    )
    alpha = arr[:, :, 3]
    arr[:, :, 3] = np.where(dark, 0, alpha)
    _knock_out_low_chroma_dark_pixels(
        arr,
        max_channel=halo_max_channel,
        chroma_max=halo_chroma_max,
    )
    if arr.shape[0] >= 32 and arr.shape[1] >= 32:
        _flood_transparent_light_edge_matte(arr)
    trimmed = trim_rgba_image_to_nontransparent_bbox(
        Image.fromarray(arr, mode="RGBA"),
        pad_px=DEFAULT_LOGO_TRIM_PAD_PX,
    )
    scaled = ensure_rgba_longest_edge_at_least(trimmed)
    out = io.BytesIO()
    scaled.save(out, format="PNG", optimize=True)
    return out.getvalue()
