#!/usr/bin/env python3
"""Alias for update_database.py: same pipeline (reviews, metadata, graph)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
UPDATE_DB_SCRIPT = SCRIPT_DIR / "update_database.py"


def main() -> int:
    cmd: list[str] = [sys.executable, str(UPDATE_DB_SCRIPT), *sys.argv[1:]]
    logger.info("Running: %s", " ".join(cmd))
    return int(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    sys.exit(main())
