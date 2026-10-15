import httpx
import pytest

from canairy.hh import HHClient, _client


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(_client.time, "sleep", lambda _: None)


def make_client(handler):
    client = HHClient()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_get_sends_a_single_get_request():
    requests = []

    def handler(request):
        requests.append(request.method)
        return httpx.Response(200, json=[])

    assert make_client(handler)._get("cores") == []
    assert requests == ["GET"]


def test_get_retries_dropped_connections():
    requests = []

    def handler(request):
        requests.append(request.method)
        if len(requests) == 1:
            raise httpx.RemoteProtocolError("dropped")
        return httpx.Response(200, json=[{"code": "no2"}])

    assert make_client(handler)._get("cores") == [{"code": "no2"}]
    assert requests == ["GET", "GET"]
