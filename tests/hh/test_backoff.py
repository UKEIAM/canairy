import httpx
import pytest

from canairy.hh import _client
from canairy.hh._client import MAX_RETRIES, backoff


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(_client.time, "sleep", lambda _: None)


def make_flaky(failures):
    calls = []

    def func():
        calls.append(1)
        if len(calls) <= failures:
            raise httpx.RemoteProtocolError("dropped")
        return "ok"

    return func, calls


def test_backoff_returns_after_transient_errors():
    func, calls = make_flaky(3)
    assert backoff(func) == "ok"
    assert len(calls) == 4


def test_backoff_reraises_when_retries_exhausted():
    func, calls = make_flaky(MAX_RETRIES)
    with pytest.raises(httpx.RemoteProtocolError):
        backoff(func)
    assert len(calls) == MAX_RETRIES


def test_backoff_does_not_retry_other_errors():
    def func():
        raise httpx.ConnectError("refused")

    with pytest.raises(httpx.ConnectError):
        backoff(func)
