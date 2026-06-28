"""Start the visual regression API with deterministic fixtures."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from music_review.api.visual_fixtures import create_visual_app

LOGGER = logging.getLogger("music_review.visual_api_server")


def main() -> None:
    """Run the visual fixture API server."""
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    LOGGER.info("Starting visual API on %s:%s", args.host, args.port)
    uvicorn.run(create_visual_app(), host=args.host, port=args.port, log_level="info")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    return parser.parse_args()


if __name__ == "__main__":
    main()
