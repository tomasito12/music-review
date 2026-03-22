#!/usr/bin/env python3
"""Alias for update_database.py: same pipeline (JSONL + Chroma by default)."""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(
        description=(
            "Same as scripts/update_database.py (reviews, metadata, imputation, "
            "chunk Chroma by default). Forwards --skip-chroma / --chroma-legacy. "
            "Other args pass through unchanged."
        ),
    )
    parser.add_argument(
        "--skip-chroma",
        action="store_true",
        help="Forward --skip-chroma (JSONL/metadata only).",
    )
    parser.add_argument(
        "--chroma-legacy",
        action="store_true",
        help="Forward --chroma-legacy (also index music_reviews collection).",
    )
    args, remainder = parser.parse_known_args()

    cmd: list[str] = [sys.executable, str(UPDATE_DB_SCRIPT), *remainder]
    if args.skip_chroma:
        cmd.append("--skip-chroma")
    if args.chroma_legacy:
        cmd.append("--chroma-legacy")

    logger.info("Running: %s", " ".join(cmd))
    return int(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    sys.exit(main())
