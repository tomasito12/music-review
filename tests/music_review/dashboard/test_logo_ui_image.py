"""Tests for dashboard logo raster helpers."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from music_review.dashboard import logo_ui_image


def _png_bytes_rgba(w: int, h: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
    """Build a tiny PNG from a flat list of RGBA tuples (row-major)."""
    arr = np.array(pixels, dtype=np.uint8).reshape((h, w, 4))
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


def test_knock_out_makes_flat_black_transparent() -> None:
    """Pure black tiles should become transparent; light pixels stay opaque."""
    png = _png_bytes_rgba(
        2,
        2,
        [
            (0, 0, 0, 255),
            (255, 255, 255, 255),
            (40, 40, 40, 255),
            (200, 200, 200, 255),
        ],
    )
    out = logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(
        png,
        rgb_threshold=50,
    )
    im = Image.open(io.BytesIO(out)).convert("RGBA")
    px = im.load()
    assert px[0, 0][3] == 0
    assert px[1, 0][:3] == (255, 255, 255) and px[1, 0][3] == 255
    assert px[0, 1][3] == 0
    assert px[1, 1][3] == 255


def test_invalid_bytes_raise_value_error() -> None:
    """Non-image input should raise a clear error."""
    with pytest.raises(ValueError, match="Invalid or unreadable"):
        logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(b"not a png")


def test_rgb_threshold_out_of_range_raises() -> None:
    """Guard impossible threshold values."""
    png = _png_bytes_rgba(1, 1, [(0, 0, 0, 255)])
    with pytest.raises(ValueError, match="rgb_threshold"):
        logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(png, rgb_threshold=-1)


def test_flood_removes_white_border_connected_to_edges() -> None:
    """Bright white padding touching borders should become transparent."""
    size = 40
    arr = np.zeros((size, size, 4), dtype=np.uint8)
    arr[:, :] = (255, 255, 255, 255)
    mid = size // 2
    arr[mid, mid] = (30, 40, 120, 255)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGBA").save(buf, format="PNG")
    out = logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(buf.getvalue())
    im = Image.open(io.BytesIO(out)).convert("RGBA")
    assert im.getpixel((0, 0))[3] == 0
    assert im.getpixel((im.size[0] // 2, im.size[1] // 2))[3] == 255


def test_trim_rgba_crops_transparent_padding() -> None:
    """Opaque content should be tightly cropped after processing."""
    arr = np.zeros((7, 7, 4), dtype=np.uint8)
    arr[3, 3] = (200, 30, 30, 255)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGBA").save(buf, format="PNG")
    out = logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(buf.getvalue())
    im = Image.open(io.BytesIO(out)).convert("RGBA")
    assert im.size == (3, 3)


def test_ensure_rgba_longest_edge_upscales_small_raster() -> None:
    """Small opaque art should be enlarged with high-quality resampling."""
    im = Image.new("RGBA", (40, 20), (200, 30, 30, 255))
    out = logo_ui_image.ensure_rgba_longest_edge_at_least(
        im,
        min_long_edge=120,
        skip_if_longest_below=8,
    )
    assert max(out.size) >= 120


def test_ensure_rgba_longest_edge_min_out_of_range_raises() -> None:
    """Invalid min long edge should raise."""
    im = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    with pytest.raises(ValueError, match="min_long_edge"):
        logo_ui_image.ensure_rgba_longest_edge_at_least(im, min_long_edge=10)


def test_trim_rgba_image_pad_out_of_range_raises() -> None:
    """Invalid pad should raise."""
    im = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    with pytest.raises(ValueError, match="pad_px"):
        logo_ui_image.trim_rgba_image_to_nontransparent_bbox(im, pad_px=-1)


def test_halo_pass_removes_low_chroma_dark_gray() -> None:
    """Dark gray anti-alias rings (low chroma) should be cleared next to art."""
    png = _png_bytes_rgba(
        3,
        1,
        [
            (20, 30, 110, 255),
            (52, 54, 56, 255),
            (20, 30, 110, 255),
        ],
    )
    out = logo_ui_image.rgba_png_bytes_with_near_black_knocked_out(png)
    im = Image.open(io.BytesIO(out)).convert("RGBA")
    assert im.getpixel((1, 0))[3] == 0
    assert im.getpixel((0, 0))[3] == 255
    assert im.getpixel((2, 0))[3] == 255
