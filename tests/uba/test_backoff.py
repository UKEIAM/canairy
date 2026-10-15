import httpx
import pytest

from canairy.uba import _client
from canairy.uba._client import MAX_RETRIES, backoff


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    sleeps = []
    monkeypatch.setattr(_client.time, "sleep", sleeps.append)
    return sleeps


def make_flaky(failures, error=None):
    calls = []

    def func():
        calls.append(1)
        request = httpx.Request("GET", "https://example.org")
        if len(calls) <= failures:
            if error is None:
                raise httpx.RemoteProtocolError("dropped")
            return httpx.Response(error, request=request)
        return httpx.Response(200, request=request)

    return func, calls


@pytest.mark.parametrize("error", [None, 429, 503])
def test_backoff_returns_after_transient_errors(error):
    func, calls = make_flaky(3, error)
    assert backoff(func).status_code == 200
    assert len(calls) == 4


@pytest.mark.parametrize(
    "error, exc",
    [(None, httpx.RemoteProtocolError), (503, httpx.HTTPStatusError)],
)
def test_backoff_reraises_when_retries_exhausted(error, exc):
    func, calls = make_flaky(MAX_RETRIES, error)
    with pytest.raises(exc):
        backoff(func)
    assert len(calls) == MAX_RETRIES


def test_backoff_does_not_sleep_after_last_attempt(sleeps):
    func, _ = make_flaky(MAX_RETRIES)
    with pytest.raises(httpx.RemoteProtocolError):
        backoff(func)
    assert sleeps == [2**i for i in range(1, MAX_RETRIES)]


@pytest.mark.parametrize("max_retries", [0, 1])
def test_backoff_without_retries_makes_one_attempt(monkeypatch, sleeps, max_retries):
    monkeypatch.setattr(_client, "MAX_RETRIES", max_retries)
    func, calls = make_flaky(0)
    assert backoff(func).status_code == 200
    func, calls = make_flaky(1)
    with pytest.raises(httpx.RemoteProtocolError):
        backoff(func)
    assert len(calls) == 1
    assert sleeps == []


def test_backoff_does_not_retry_client_errors():
    func, calls = make_flaky(1, 404)
    with pytest.raises(httpx.HTTPStatusError):
        backoff(func)
    assert len(calls) == 1
