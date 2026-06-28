"""Shared HTTP user-agent headers for enrichment API clients."""

from __future__ import annotations

from os import getenv

USER_AGENT_APP = getenv("USER_AGENT_APP", "music-review")
USER_AGENT_VERSION = getenv("USER_AGENT_VERSION", "0.1.0")
USER_AGENT_CONTACT = getenv("USER_AGENT_CONTACT", "mailto:you@example.com")

WIKIMEDIA_HEADERS = {
    "User-Agent": f"{USER_AGENT_APP}/{USER_AGENT_VERSION} ({USER_AGENT_CONTACT})",
}
