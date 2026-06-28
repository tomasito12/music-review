"""Tests for scripts/server.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_SH = REPO_ROOT / "scripts" / "server.sh"


def _run_server_sh(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run server.sh with a clean environment override."""
    run_env = os.environ.copy()
    run_env["MUSIC_REVIEW_SERVER_DRY_RUN"] = "true"
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", str(SERVER_SH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=run_env,
    )


def test_server_sh_help_lists_core_commands() -> None:
    """Help output documents the main server operations."""
    result = _run_server_sh("--help")
    assert result.returncode == 0
    assert "prod-update" in result.stdout
    assert "install-hourly-cron" in result.stdout
    assert "start-artist-image-batch" in result.stdout


def test_server_sh_unknown_command_fails() -> None:
    """Unknown subcommands exit with an error."""
    result = _run_server_sh("not-a-command")
    assert result.returncode != 0
    assert "Unknown command" in result.stderr


def test_server_sh_status_dry_run_prints_ssh_target() -> None:
    """Status in dry-run mode shows the configured SSH target without connecting."""
    result = _run_server_sh(
        "status",
        env={
            "MUSIC_REVIEW_SYNC_HOST": "example.test",
            "MUSIC_REVIEW_SYNC_USER": "deploy",
        },
    )
    assert result.returncode == 0
    assert "DRY_RUN ssh" in result.stdout
    assert "deploy@example.test" in result.stdout


def test_server_sh_prod_update_dry_run_mentions_compose_profile() -> None:
    """Prod-update dry-run references the jobs compose profile."""
    result = _run_server_sh("prod-update")
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "music-review-update" in combined
    assert "--profile jobs" in combined


def test_server_sh_install_cron_dry_run_invokes_installer() -> None:
    """Cron install dry-run delegates to install_production_cron.sh on the server."""
    result = _run_server_sh("install-cron")
    assert result.returncode == 0
    assert "install_production_cron.sh" in result.stdout


def test_server_sh_install_hourly_cron_is_alias() -> None:
    """Legacy install-hourly-cron command remains available."""
    result = _run_server_sh("install-hourly-cron")
    assert result.returncode == 0
    assert "install_production_cron.sh" in result.stdout + result.stderr
