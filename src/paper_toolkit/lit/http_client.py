"""Polite HTTP GET wrapper used by the lit-search adapters.

Why stdlib over httpx / requests: the toolkit is meant to be drop-in on
constrained CI runners and Docker images. urllib avoids dragging in a
parallel HTTP stack just for three GET endpoints. The wrapper still
covers the basics: a sane User-Agent, optional `mailto` for CrossRef /
OpenAlex politeness, a small retry loop, and a `client` injection point
so tests never hit the network.
"""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass


class HttpError(RuntimeError):
    """Raised when an upstream GET ultimately fails (after retries)."""


@dataclass(frozen=True)
class HttpResponse:
    """Captured response payload from a successful GET."""

    url: str
    status: int
    body: bytes
    content_type: str

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


HttpClient = Callable[[str, dict[str, str]], HttpResponse]
"""Signature for the injectable HTTP client: `(url, headers) -> HttpResponse`."""


def _user_agent() -> str:
    mailto = os.environ.get("PAPER_TOOLKIT_MAILTO", "").strip()
    base = "paper-toolkit/0.1 (+https://github.com/fib-lab/paper-toolkit)"
    return f"{base} mailto:{mailto}" if mailto else base


def _mailto() -> str | None:
    value = os.environ.get("PAPER_TOOLKIT_MAILTO", "").strip()
    return value or None


def add_mailto_param(url: str) -> str:
    """Append `mailto=...` to a URL when PAPER_TOOLKIT_MAILTO is set.

    CrossRef and OpenAlex prioritize traffic that identifies a contact
    address — we use it when available, no-op otherwise.
    """
    mailto = _mailto()
    if not mailto:
        return url
    parsed = urllib.parse.urlparse(url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("mailto", mailto)
    encoded = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(parsed._replace(query=encoded))


def default_http_get(url: str, headers: dict[str, str]) -> HttpResponse:
    """Issue a real urllib GET. Tests should inject a fake instead."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return HttpResponse(
                url=resp.geturl(),
                status=resp.status,
                body=body,
                content_type=resp.headers.get("Content-Type", ""),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read() if exc.fp is not None else b""
        return HttpResponse(
            url=url,
            status=exc.code,
            body=body,
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
        )
    except urllib.error.URLError as exc:
        raise HttpError(f"URLError requesting {url}: {exc.reason}") from exc


def polite_get(
    url: str,
    *,
    accept: str = "application/json",
    client: HttpClient | None = None,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
) -> HttpResponse:
    """GET `url` with retries and a recognizable User-Agent.

    `client` defaults to `default_http_get` (real network). Pass a fake
    in tests. Status >= 500 triggers a retry; 4xx and 2xx return
    immediately.
    """
    headers = {"User-Agent": _user_agent(), "Accept": accept}
    runner = client or default_http_get
    last_response: HttpResponse | None = None
    for attempt in range(1, max_attempts + 1):
        response = runner(url, headers)
        last_response = response
        if 200 <= response.status < 300:
            return response
        if response.status >= 500 and attempt < max_attempts:
            time.sleep(backoff_seconds * attempt)
            continue
        return response
    # Defensive — the loop above always returns or sleeps.
    assert last_response is not None
    return last_response
