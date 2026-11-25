"""HTTP plumbing shared by all clients: rate limiting, retries and caching.

Transport stack (outermost first)::

    httpx2.Client → CacheTransport → RetryTransport → RateLimitTransport → HTTPTransport

The limiter sits below the cache, so cache hits do not count against the
budget, and below the retry layer, so every retry does.
"""

import logging
import threading
import time
from collections import deque

import httpx2
from hishel.httpx2 import CacheTransport

__all__ = [
    "CALLS",
    "MAX_RETRIES",
    "PERIOD",
    "UBA_RETRY_STATUSES",
    "RateLimitTransport",
    "RateLimiter",
    "RetryTransport",
    "build_client",
    "build_transport",
    "limiter_for",
]

logger = logging.getLogger(__name__)

CALLS = 120
PERIOD = 60
MAX_RETRIES = 8
UBA_RETRY_STATUSES = frozenset({429, *range(500, 600)})


class RateLimiter:
    """Allow at most ``calls`` acquisitions in any ``period`` seconds."""

    def __init__(self, calls: int, period: float) -> None:
        self.calls = calls
        self.period = period
        self._stamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        # Waiting under the lock serializes waiting threads, which is fine for
        # a limit of this size.
        with self._lock:
            now = time.monotonic()
            while self._stamps and now - self._stamps[0] >= self.period:
                self._stamps.popleft()
            if len(self._stamps) >= self.calls:
                wait = self._stamps[0] + self.period - now
                logger.debug(f"rate limit reached: sleeping {wait:.1f} s")
                time.sleep(wait)
                self._stamps.popleft()
                now = time.monotonic()
            self._stamps.append(now)


_LIMITERS: dict[str, RateLimiter] = {}
_LIMITERS_LOCK = threading.Lock()


def limiter_for(host: str) -> RateLimiter:
    """Return the process-wide limiter for ``host``, creating it on first use."""
    with _LIMITERS_LOCK:
        if host not in _LIMITERS:
            _LIMITERS[host] = RateLimiter(CALLS, PERIOD)
        return _LIMITERS[host]


class RateLimitTransport(httpx2.BaseTransport):
    """Throttle requests per host before passing them on."""

    def __init__(self, next_transport: httpx2.BaseTransport) -> None:
        self.next_transport = next_transport

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        limiter_for(request.url.host).acquire()
        return self.next_transport.handle_request(request)

    def close(self) -> None:
        self.next_transport.close()


class RetryTransport(httpx2.BaseTransport):
    """Retry dropped connections and ``retry_statuses`` with exponential backoff.

    Makes at most ``max_retries`` attempts (at least one), sleeping ``2**i``
    seconds between them. Once they are exhausted, the last error is raised or
    the last response returned. Timeouts and connect errors are not retried.
    """

    def __init__(
        self,
        next_transport: httpx2.BaseTransport,
        retry_statuses: frozenset[int] = frozenset(),
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.next_transport = next_transport
        self.retry_statuses = retry_statuses
        self.max_retries = max_retries

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        base = 2
        for i in range(1, self.max_retries):
            try:
                response = self._attempt(request)
            except httpx2.RemoteProtocolError:
                logger.debug(f"RemoteProtocolError: retry {i}")
            else:
                if response.status_code not in self.retry_statuses:
                    return response
                logger.debug(f"HTTP {response.status_code}: retry {i}")
            time.sleep(base**i)
        # The last attempt (the only one if max_retries <= 1) raises its error.
        return self._attempt(request)

    def _attempt(self, request: httpx2.Request) -> httpx2.Response:
        response = self.next_transport.handle_request(request)
        if isinstance(response.stream, httpx2.ByteStream):
            return response  # already in memory (httpx2 reads these eagerly)
        # Read the body here: a connection dropped mid-body raises
        # RemoteProtocolError while reading, which must be retried too.
        try:
            raw = b"".join(response.iter_raw())
        finally:
            response.close()
        # Raw (still encoded) bytes keep Content-Encoding valid upstream.
        return httpx2.Response(
            response.status_code,
            headers=response.headers,
            stream=httpx2.ByteStream(raw),
            extensions=response.extensions,
            request=request,
        )

    def close(self) -> None:
        self.next_transport.close()


def build_transport(
    inner: httpx2.BaseTransport, retry_statuses: frozenset[int] = frozenset()
) -> httpx2.BaseTransport:
    """Wrap ``inner`` in the rate limit and retry layers."""
    return RetryTransport(RateLimitTransport(inner), retry_statuses)


def build_client(retry_statuses: frozenset[int] = frozenset()) -> httpx2.Client:
    """Build a caching, rate-limited, retrying client.

    ``rfc=True`` keeps RFC 9111 semantics: hishel 2.0's default ignores
    ``Cache-Control`` and caches every GET forever. Because an explicit
    transport is passed, proxies from ``HTTP(S)_PROXY`` bypass this stack.
    """
    transport = CacheTransport(
        next_transport=build_transport(httpx2.HTTPTransport(), retry_statuses),
        rfc=True,
    )
    return httpx2.Client(timeout=60, transport=transport)
