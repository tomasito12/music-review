from __future__ import annotations

import importlib


def test_neueste_reviews_pool_importable() -> None:
    module = importlib.import_module("pages.neueste_reviews_pool")
    assert hasattr(module, "fetch_newest_reviews_pool")
    assert hasattr(module, "ensure_neueste_session_defaults")
    assert hasattr(module, "RECENT_DEFAULT")
