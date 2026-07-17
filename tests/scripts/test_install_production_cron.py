"""Tests for scripts/install_production_cron.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_CRON_SH = REPO_ROOT / "scripts" / "install_production_cron.sh"
CRON_TEMPLATE = REPO_ROOT / "deploy" / "production.crontab"


def _run_install_cron(
    *,
    deploy_path: str,
    crontab_target: Path,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DEPLOY_PATH"] = deploy_path
    env["CRONTAB_TARGET"] = str(crontab_target)
    if dry_run:
        env["CRONTAB_DRY_RUN"] = "true"
    return subprocess.run(
        ["bash", str(INSTALL_CRON_SH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_production_crontab_contains_managed_markers() -> None:
    """The committed cron template is wrapped in managed markers."""
    text = CRON_TEMPLATE.read_text(encoding="utf-8")
    assert "# music-review-managed-begin" in text
    assert "# music-review-managed-end" in text
    assert "__DEPLOY_PATH__" in text
    assert "--profile jobs" in text


def test_install_production_cron_writes_managed_block(tmp_path: Path) -> None:
    """Installer replaces the deploy path and writes a managed cron block."""
    target = tmp_path / "crontab.txt"
    target.write_text(
        "0 3 * * * /usr/bin/backup\n"
        "# music-review-managed-begin\n"
        "0 * * * * cd /old/path && docker compose run --rm music-review-update\n"
        "# music-review-managed-end\n",
        encoding="utf-8",
    )
    result = _run_install_cron(
        deploy_path="/srv/music-review",
        crontab_target=target,
    )
    assert result.returncode == 0, result.stderr
    merged = target.read_text(encoding="utf-8")
    assert "0 3 * * * /usr/bin/backup" in merged
    assert "/old/path" not in merged
    assert "cd /srv/music-review" in merged
    assert merged.count("# music-review-managed-begin") == 1


def test_install_production_cron_removes_legacy_hourly_update_line(
    tmp_path: Path,
) -> None:
    """Installer removes old unmanaged hourly update entries."""
    target = tmp_path / "crontab.txt"
    target.write_text(
        "0 * * * * cd /srv/music-review && mkdir -p logs && "
        "docker compose --profile jobs run --rm music-review-update "
        ">> logs/hourly-update.log 2>&1\n"
        "# Managed production cron for music-review (Infrastructure as Code).\n"
        "15 2 * * * /usr/bin/backup\n",
        encoding="utf-8",
    )

    result = _run_install_cron(
        deploy_path="/srv/music-review",
        crontab_target=target,
    )

    assert result.returncode == 0, result.stderr
    merged = target.read_text(encoding="utf-8")
    assert "15 2 * * * /usr/bin/backup" in merged
    assert merged.count("music-review-update") == 1
    assert "Managed production cron for music-review" in merged


def test_install_production_cron_dry_run_prints_schedule(tmp_path: Path) -> None:
    """Dry-run mode prints the merged crontab without requiring crontab(1)."""
    target = tmp_path / "crontab.txt"
    result = _run_install_cron(
        deploy_path="/srv/music-review",
        crontab_target=target,
        dry_run=True,
    )
    assert result.returncode == 0, result.stderr
    assert "0 * * * *" in result.stdout
    assert "/srv/music-review" in result.stdout
