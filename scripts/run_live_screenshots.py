"""Run Playwright live screenshot tests with the visual fixture API and frontend."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

LOGGER = logging.getLogger("music_review.run_live_screenshots")
ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
API_URL = "http://127.0.0.1:8010/health"
FRONTEND_URL = "http://127.0.0.1:5173/"
PNPM_VERSION = "10.12.1"


def main() -> None:
    """Start services, run Playwright, then shut everything down."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    api = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/visual_api_server.py"), "--port", "8010"],
        cwd=ROOT,
    )
    frontend_env = os.environ.copy()
    frontend_env["VITE_API_BASE_URL"] = "http://127.0.0.1:8010"
    frontend = subprocess.Popen(
        [
            "pnpm",
            "dev",
            "--host",
            "127.0.0.1",
            "--port",
            "5173",
        ],
        cwd=FRONTEND,
        env=frontend_env,
    )

    exit_code = 1
    try:
        _ensure_pnpm()
        _wait_for_url(API_URL)
        _wait_for_url(FRONTEND_URL)
        playwright_cmd = [
            "pnpm",
            "exec",
            "playwright",
            "test",
            "--project=live",
        ]
        if args.update_snapshots:
            playwright_cmd.append("--update-snapshots")
        result = subprocess.run(
            playwright_cmd,
            cwd=FRONTEND,
            env=frontend_env,
            check=False,
        )
        exit_code = result.returncode
    finally:
        _terminate(frontend)
        _terminate(api)

    raise SystemExit(exit_code)


def _ensure_pnpm() -> None:
    """Activate the pinned pnpm version when it is not already on PATH."""
    if shutil.which("pnpm") is not None:
        return
    subprocess.run(["corepack", "enable"], check=True)
    subprocess.run(
        ["corepack", "prepare", f"pnpm@{PNPM_VERSION}", "--activate"],
        check=True,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-snapshots",
        action="store_true",
        help="Refresh committed reference screenshots.",
    )
    return parser.parse_args()


def _wait_for_url(url: str, *, timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code < 500:
                LOGGER.info("Ready: %s", url)
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    msg = f"Timed out waiting for {url}"
    raise TimeoutError(msg)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()
