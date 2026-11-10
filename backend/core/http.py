"""The shared outbound HTTP client handed to modules."""

from __future__ import annotations

import httpx

from core.config import Config

USER_AGENT = "weather-aware-truck-routing/1.0 (+https://github.com/; assessment project)"


def build_http_client(config: Config) -> httpx.Client:
    """One pooled client per process.

    Retries cover connection failures only (the transport never retries a request
    that reached the server), so a slow upstream is never hit twice by us.
    """
    return httpx.Client(
        timeout=httpx.Timeout(config.http_timeout_s, connect=5.0),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        transport=httpx.HTTPTransport(retries=2),
        follow_redirects=False,
    )
