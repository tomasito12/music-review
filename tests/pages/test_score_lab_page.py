"""Smoke tests for the Score Lab Streamlit page module."""

from __future__ import annotations

import importlib


def test_score_lab_page_module_imports() -> None:
    module = importlib.import_module("pages.7_Score_Lab")
    assert hasattr(module, "main")
    assert callable(module.main)


def test_score_lab_widget_key_helper() -> None:
    module = importlib.import_module("pages.7_Score_Lab")
    assert module._widget_key("alpha") == "score_lab_alpha"
