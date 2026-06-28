"""Tests for the live screenshot orchestrator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "run_live_screenshots.py"
)


def _load_run_live_screenshots_module():
    spec = importlib.util.spec_from_file_location(
        "run_live_screenshots",
        _MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wait_for_url_accepts_successful_response() -> None:
    module = _load_run_live_screenshots_module()
    response = MagicMock()
    response.status_code = 200
    with patch.object(module.httpx, "get", return_value=response):
        module._wait_for_url("http://127.0.0.1:8010/health", timeout_seconds=5.0)


def test_wait_for_url_raises_when_service_stays_down() -> None:
    module = _load_run_live_screenshots_module()
    with (
        patch.object(module.httpx, "get", side_effect=module.httpx.HTTPError("down")),
        pytest.raises(TimeoutError, match="Timed out waiting for"),
    ):
        module._wait_for_url("http://127.0.0.1:9", timeout_seconds=0.6)
