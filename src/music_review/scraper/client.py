# src/music_review/scraper/client.py

from __future__ import annotations

import logging
import random
import time
from typing import Iterable, Iterator

import httpx

logger = logging.getLogger(__name__)


BASE_URL = "https://www.plattentests.de/rezi.php"
DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_REQUESTS_PER_SECOND = 2.5


class RateLimiter:
    """Simple rate limiter for 'medium' scraping speed.

    Ensures we do not exceed roughly `max_per_second` requests per second.
    A small random jitter is added to avoid perfectly regular patterns.
    """

    def __init__(self, max_per_second: float = DEFAULT_MAX_REQUESTS_PER_SECOND) -> None:
        if max_per_second <= 0:
            msg = "max_per_second must be positive."
            raise ValueError(msg)

        self._min_interval = 1.0 / max_per_second
        self._last_call: float | None = None

    def wait(self) -> None:
        """Sleep just enough to respect the configured rate limit."""
        now = time.monotonic()
        if self._last_call is None:
            self._last_call = now
            return

        elapsed = now - self._last_call
        # Add a small random jitter up to 150 ms.
        jitter = random.uniform(0.0, 0.15)
        target_interval = self._min_interval + jitter

        if elapsed < target_interval:
            time.sleep(target_interval - elapsed)

        self._last_call = time.monotonic()


class ScraperClient:
    """HTTP client for fetching review pages from plattentests.de."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: str | None = None,
    ) -> None:
        if max_retries < 0:
            msg = "max_retries must be non-negative."
            raise ValueError(msg)

        self._base_url = BASE_URL
        self._max_retries = max_retries

        headers = {
            "User-Agent": user_agent
            or "music-review-scraper/0.1 (+https://example.com)",
            "Accept": "text/html,application/xhtml+xml",
        }

        self._client = httpx.Client(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "ScraperClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def build_url(self, review_id: int) -> str:
        """Build the review URL for a given numeric ID."""
        return f"{self._base_url}?show={review_id}"

    def fetch_html(self, review_id: int) -> str | None:
        """Fetch raw HTML for a given review ID.

        Returns:
            The HTML content as a string, or None if the page does not exist
            (404) or if all retries failed.

        Notes:
            - 404 is treated as "review does not exist" and returns None without
              additional retries.
            - 5xx errors and network issues are retried up to `max_retries`.
        """
        url = self.build_url(review_id)

        for attempt in range(1, self._max_retries + 2):
            try:
                response = self._client.get(url)

                if response.status_code == 404:
                    logger.info("Review %s not found (404).", review_id)
                    return None

                response.raise_for_status()
                logger.debug(
                    "Fetched review %s (status=%s).",
                    review_id,
                    response.status_code,
                )
                return response.text
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                # Retry only on 5xx errors.
                if 500 <= status < 600 and attempt <= self._max_retries:
                    logger.warning(
                        "Server error for review %s (status=%s, attempt=%s/%s). "
                        "Retrying...",
                        review_id,
                        status,
                        attempt,
                        self._max_retries,
                    )
                    _sleep_backoff(attempt)
                    continue

                logger.error(
                    "Unrecoverable HTTP error for review %s (status=%s): %s",
                    review_id,
                    status,
                    exc,
                )
                return None
            except httpx.RequestError as exc:
                if attempt <= self._max_retries:
                    logger.warning(
                        "Request error for review %s (attempt=%s/%s): %s. Retrying...",
                        review_id,
                        attempt,
                        self._max_retries,
                        exc,
                    )
                    _sleep_backoff(attempt)
                    continue

                logger.error(
                    "Request error for review %s after %s attempts: %s",
                    review_id,
                    attempt - 1,
                    exc,
                )
                return None

        # Shouldn't be reached, but keeps mypy happy.
        return None


def iter_review_html(
    client: ScraperClient,
    review_ids: Iterable[int],
    rate_limiter: RateLimiter | None = None,
) -> Iterator[tuple[int, str | None]]:
    """Iterate over review IDs and yield (id, html) pairs.

    Args:
        client: The ScraperClient instance to use for HTTP calls.
        review_ids: Iterable of numeric review IDs to fetch.
        rate_limiter: Optional RateLimiter instance. If provided, its `wait()`
            method is called before each request.

    Yields:
        Tuples of (review_id, html_or_none), where html_or_none is None if the
        review does not exist or all retries failed.
    """
    for review_id in review_ids:
        if rate_limiter is not None:
            rate_limiter.wait()

        html = client.fetch_html(review_id)
        yield review_id, html


def _sleep_backoff(attempt: int) -> None:
    """Sleep for a short exponential backoff based on the attempt number."""
    base = 0.5
    max_sleep = 5.0
    delay = min(max_sleep, base * (2 ** (attempt - 1)))
    jitter = random.uniform(0.0, 0.25 * delay)
    time.sleep(delay + jitter)
