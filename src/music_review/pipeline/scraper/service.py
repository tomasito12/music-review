"""Core scraping service logic, decoupled from CLI argument parsing."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from music_review.io.reviews_jsonl import review_to_raw
from music_review.pipeline.scraper.client import (
    RateLimiter,
    ScraperClient,
    iter_review_html,
)
from music_review.pipeline.scraper.parser import parse_review
from music_review.pipeline.scraper.storage import (
    append_review,
    load_corpus,
    write_corpus,
)

logger = logging.getLogger(__name__)


class ScrapeResult:
    """Collects scraping statistics."""

    def __init__(self) -> None:
        self.processed: int = 0
        self.scraped_ids: list[int] = []


def scrape_ids(
    ids: Iterable[int],
    *,
    output_path: Path,
    max_rps: float,
    update_mode: bool = False,
    log_every: int = 50,
) -> ScrapeResult:
    """Scrape a sequence of review IDs and persist results.

    Args:
        ids: Review IDs to scrape.
        output_path: JSONL file to write/append to.
        max_rps: Maximum requests per second.
        update_mode: If True, overwrite existing entries (loads full corpus).
                     If False, append new entries only.
        log_every: Log progress every N reviews.
    """
    rate_limiter = RateLimiter(max_per_second=max_rps)
    corpus = _load_corpus_if_update(output_path, update_mode)
    result = ScrapeResult()

    with ScraperClient() as client:
        for review_id, html in iter_review_html(client, ids, rate_limiter=rate_limiter):
            if html is None:
                continue
            _process_single(review_id, html, output_path, corpus, update_mode, result)
            if result.processed % log_every == 0:
                logger.info("Processed %s reviews so far.", result.processed)

    _finalize_corpus(corpus, update_mode, output_path, result)
    return result


def scrape_until_gap(
    start_id: int,
    *,
    output_path: Path,
    max_rps: float,
    update_mode: bool = False,
    stop_after_n_empty: int = 3,
    log_every: int = 50,
) -> ScrapeResult:
    """Scrape from ``start_id`` upward until N consecutive missing IDs.

    Args:
        start_id: First ID to try.
        output_path: JSONL file to write/append to.
        max_rps: Maximum requests per second.
        update_mode: If True, overwrite existing entries.
        stop_after_n_empty: Stop after this many consecutive missing IDs.
        log_every: Log progress every N reviews.
    """
    if stop_after_n_empty < 1:
        msg = "stop_after_n_empty must be >= 1."
        raise ValueError(msg)

    rate_limiter = RateLimiter(max_per_second=max_rps)
    corpus = _load_corpus_if_update(output_path, update_mode)
    result = ScrapeResult()

    consecutive_empty = 0
    current_id = start_id

    with ScraperClient() as client:
        while True:
            rate_limiter.wait()
            html = client.fetch_html(current_id)

            if html is None:
                consecutive_empty += 1
                if consecutive_empty >= stop_after_n_empty:
                    logger.info(
                        "Stopping: %s consecutive missing IDs (from ID %s onward).",
                        stop_after_n_empty,
                        current_id - stop_after_n_empty + 1,
                    )
                    break
                current_id += 1
                continue

            consecutive_empty = 0
            _process_single(current_id, html, output_path, corpus, update_mode, result)
            current_id += 1

            if result.processed % log_every == 0 and result.processed > 0:
                logger.info("Processed %s reviews so far.", result.processed)

    _finalize_corpus(corpus, update_mode, output_path, result)
    return result


def _load_corpus_if_update(
    output_path: Path,
    update_mode: bool,
) -> dict[int, dict[str, Any]] | None:
    """Load existing corpus when in update mode."""
    if update_mode and output_path.exists():
        corpus = load_corpus(output_path)
        logger.info(
            "Loaded existing corpus from %s with %s reviews.",
            output_path,
            len(corpus),
        )
        return corpus
    return None


def _process_single(
    review_id: int,
    html: str,
    output_path: Path,
    corpus: dict[int, dict[str, Any]] | None,
    update_mode: bool,
    result: ScrapeResult,
) -> None:
    """Parse one HTML page and store the review."""
    review = parse_review(review_id, html)
    if review is None:
        return

    if update_mode:
        assert corpus is not None
        corpus[review.id] = review_to_raw(review)
    else:
        append_review(output_path, review)

    result.scraped_ids.append(review.id)
    result.processed += 1


def _finalize_corpus(
    corpus: dict[int, dict[str, Any]] | None,
    update_mode: bool,
    output_path: Path,
    result: ScrapeResult,
) -> None:
    """Write the full corpus to disk if in update mode."""
    if update_mode and corpus is not None:
        ordered = [corpus[i] for i in sorted(corpus.keys())]
        write_corpus(output_path, ordered)
        logger.info(
            "Mode 'update': wrote %s reviews (including %s updated IDs) to %s.",
            len(ordered),
            len(result.scraped_ids),
            output_path,
        )
    else:
        logger.info("Done. Processed %s reviews.", result.processed)
