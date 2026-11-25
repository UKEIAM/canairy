import gzip

import httpx2
import pytest

from canairy import _http
from canairy._http import (
    CALLS,
    MAX_RETRIES,
    PERIOD,
    UBA_RETRY_STATUSES,
    RetryTransport,
    build_transport,
    limiter_for,
)


class FakeTime:
    """Stands in for the ``time`` module: sleeping advances the clock."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    clock = FakeTime()
    monkeypatch.setattr(_http, "time", clock)
    monkeypatch.setattr(_http, "_LIMITERS", {})
    return clock


class NetworkStream(httpx2.SyncByteStream):
    """A body that is streamed like a real network response."""

    def __init__(self, body):
        self.body = body

    def __iter__(self):
        yield self.body


class FailingStream(httpx2.SyncByteStream):
    """A body that drops the connection while being read."""

    def __iter__(self):
        yield b'{"partial'
        raise httpx2.RemoteProtocolError("peer closed connection")


def make_flaky(failures, error=None):
    """Mock transport failing ``failures`` times: dropped, status or mid-body."""
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) <= failures:
            if error is None:
                raise httpx2.RemoteProtocolError("dropped")
            if error == "body":
                return httpx2.Response(200, stream=FailingStream())
            return httpx2.Response(error)
        return httpx2.Response(200, json={"ok": True})

    return httpx2.MockTransport(handler), calls


def get(transport, url="https://example.org/x"):
    with httpx2.Client(transport=transport) as client:
        return client.get(url)


# Retries


@pytest.mark.parametrize("error", [None, "body", 429, 503])
def test_retry_returns_after_transient_errors(error):
    mock, calls = make_flaky(3, error)
    response = get(RetryTransport(mock, UBA_RETRY_STATUSES))
    assert response.json() == {"ok": True}
    assert len(calls) == 4


@pytest.mark.parametrize("error", [None, "body"])
def test_retry_reraises_when_retries_exhausted(error):
    mock, calls = make_flaky(MAX_RETRIES, error)
    with pytest.raises(httpx2.RemoteProtocolError):
        get(RetryTransport(mock))
    assert len(calls) == MAX_RETRIES


def test_retry_returns_last_response_when_retries_exhausted():
    mock, calls = make_flaky(MAX_RETRIES, 503)
    assert get(RetryTransport(mock, UBA_RETRY_STATUSES)).status_code == 503
    assert len(calls) == MAX_RETRIES


def test_retry_does_not_sleep_after_last_attempt(clock):
    mock, _ = make_flaky(MAX_RETRIES)
    with pytest.raises(httpx2.RemoteProtocolError):
        get(RetryTransport(mock))
    assert clock.sleeps == [2**i for i in range(1, MAX_RETRIES)]


@pytest.mark.parametrize("max_retries", [0, 1])
def test_retry_without_retries_makes_one_attempt(clock, max_retries):
    mock, calls = make_flaky(0)
    assert get(RetryTransport(mock, max_retries=max_retries)).status_code == 200
    mock, calls = make_flaky(1)
    with pytest.raises(httpx2.RemoteProtocolError):
        get(RetryTransport(mock, max_retries=max_retries))
    assert len(calls) == 1
    assert clock.sleeps == []


@pytest.mark.parametrize(
    "error, statuses",
    [(404, UBA_RETRY_STATUSES), (503, frozenset())],
)
def test_retry_returns_other_statuses_at_once(error, statuses):
    mock, calls = make_flaky(1, error)
    assert get(RetryTransport(mock, statuses)).status_code == error
    assert len(calls) == 1


def test_retry_does_not_retry_other_errors():
    def handler(request):
        raise httpx2.ConnectError("refused")

    with pytest.raises(httpx2.ConnectError):
        get(RetryTransport(httpx2.MockTransport(handler)))


def test_retry_keeps_encoded_body_decodable():
    body = gzip.compress(b'{"ok": true}')

    def handler(request):
        headers = {"Content-Encoding": "gzip"}
        return httpx2.Response(200, headers=headers, stream=NetworkStream(body))

    assert get(RetryTransport(httpx2.MockTransport(handler))).json() == {"ok": True}


# Rate limiting


def test_limiter_sleeps_once_budget_is_spent(clock):
    limiter = limiter_for("example.org")
    for _ in range(CALLS):
        limiter.acquire()
        clock.now += 0.1
    assert clock.sleeps == []
    limiter.acquire()
    assert clock.sleeps == [pytest.approx(PERIOD - CALLS * 0.1)]


def test_limiter_does_not_sleep_when_calls_are_spread_out(clock):
    limiter = limiter_for("example.org")
    for _ in range(3 * CALLS):
        limiter.acquire()
        clock.now += PERIOD / CALLS
    assert clock.sleeps == []


def test_limiter_budget_is_per_host(clock):
    for _ in range(CALLS):
        limiter_for("a.example.org").acquire()
    limiter_for("b.example.org").acquire()
    assert clock.sleeps == []
    limiter_for("a.example.org").acquire()
    assert clock.sleeps == [PERIOD]


def test_limiter_for_returns_same_limiter_per_host():
    assert limiter_for("example.org") is limiter_for("example.org")
    assert limiter_for("example.org") is not limiter_for("example.com")


def test_retries_count_against_the_limit(clock):
    mock, calls = make_flaky(2)
    get(build_transport(mock))
    assert len(limiter_for("example.org")._stamps) == len(calls) == 3
