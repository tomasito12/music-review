"""Tests for the plattentests.de scraper HTTP client and rate limiter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from music_review.pipeline.scraper.client import (
    BASE_URL,
    RateLimiter,
    ScraperClient,
    iter_review_html,
)


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    """Build a mock HTTP response that does not require a request (avoids raise_for_status RuntimeError)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=resp,
        )
    return resp


def test_rate_limiter_rejects_non_positive_max_per_second() -> None:
    """RateLimiter raises ValueError when max_per_second is not positive."""
    with pytest.raises(ValueError, match="must be positive"):
        RateLimiter(max_per_second=0)
    with pytest.raises(ValueError, match="must be positive"):
        RateLimiter(max_per_second=-1.0)


def test_rate_limiter_wait_does_not_raise() -> None:
    """wait() can be called without error; first call does not block."""
    limiter = RateLimiter(max_per_second=10.0)
    limiter.wait()
    limiter.wait()


def test_scraper_client_build_url() -> None:
    """build_url returns the plattentests.de review URL for the given ID."""
    client = ScraperClient()
    try:
        assert client.build_url(123) == f"{BASE_URL}?show=123"
        assert client.build_url(1) == f"{BASE_URL}?show=1"
    finally:
        client.close()


def test_scraper_client_rejects_negative_retries() -> None:
    """ScraperClient raises ValueError when max_retries is negative."""
    with pytest.raises(ValueError, match="non-negative"):
        ScraperClient(max_retries=-1)


def test_scraper_client_context_manager() -> None:
    """ScraperClient can be used as a context manager; close is called on exit."""
    with ScraperClient() as client:
        assert client.build_url(1) == f"{BASE_URL}?show=1"
    # close() was called; using the client after exit would be invalid in real use


def test_fetch_html_returns_none_on_404() -> None:
    """fetch_html returns None when the server responds with 404."""
    client = ScraperClient(max_retries=0)
    client._client = MagicMock()
    client._client.get.return_value = _mock_response(404, text="Not Found")
    try:
        assert client.fetch_html(999) is None
    finally:
        client.close()


def test_fetch_html_returns_none_on_array_is_empty() -> None:
    """fetch_html returns None when the page returns 200 but body contains 'Array is empty'."""
    client = ScraperClient(max_retries=0)
    client._client = MagicMock()
    client._client.get.return_value = _mock_response(
        200,
        text="Error: Array is empty\nWenn Du uns helfen möchtest...",
    )
    try:
        assert client.fetch_html(21411) is None
    finally:
        client.close()


def test_fetch_html_returns_text_on_success() -> None:
    """fetch_html returns the response text when status is 200 and body is valid."""
    client = ScraperClient(max_retries=0)
    html = "<html><body>Review content</body></html>"
    client._client = MagicMock()
    client._client.get.return_value = _mock_response(200, text=html)
    try:
        assert client.fetch_html(1) == html
    finally:
        client.close()


def test_iter_review_html_yields_id_and_html() -> None:
    """iter_review_html yields (review_id, html_or_none) for each requested ID."""
    client = ScraperClient(max_retries=0)
    client._client = MagicMock()
    client._client.get.side_effect = [
        _mock_response(200, text="<html>1</html>"),
        _mock_response(404),
        _mock_response(200, text="<html>3</html>"),
    ]
    try:
        ids = [1, 2, 3]
        results = list(iter_review_html(client, ids, rate_limiter=None))
        assert len(results) == 3
        assert results[0] == (1, "<html>1</html>")
        assert results[1] == (2, None)
        assert results[2] == (3, "<html>3</html>")
    finally:
        client.close()


def test_fetch_html_returns_none_on_4xx() -> None:
    """fetch_html returns None for 4xx responses (other than 404) without retrying."""
    client = ScraperClient(max_retries=0)
    client._client = MagicMock()
    client._client.get.return_value = _mock_response(403, text="Forbidden")
    try:
        assert client.fetch_html(1) is None
    finally:
        client.close()
    client._client.get.assert_called_once()


def test_fetch_html_retries_on_5xx_then_succeeds() -> None:
    """fetch_html retries on 5xx and returns content when a later attempt succeeds."""
    client = ScraperClient(max_retries=1)
    client._client = MagicMock()
    html = "<html>OK</html>"
    client._client.get.side_effect = [
        _mock_response(500, text="Server Error"),
        _mock_response(200, text=html),
    ]
    with patch("music_review.pipeline.scraper.client._sleep_backoff"):
        try:
            assert client.fetch_html(1) == html
        finally:
            client.close()
    assert client._client.get.call_count == 2


def test_fetch_html_returns_none_after_request_errors_exhausted() -> None:
    """fetch_html returns None when all retries fail with RequestError."""
    client = ScraperClient(max_retries=1)
    client._client = MagicMock()
    client._client.get.side_effect = httpx.RequestError("connection failed")
    with patch("music_review.pipeline.scraper.client._sleep_backoff"):
        try:
            assert client.fetch_html(1) is None
        finally:
            client.close()
    assert client._client.get.call_count == 2
