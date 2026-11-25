import httpx2
import pytest

from canairy import _http
from canairy.hh import HHClient


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(_http.time, "sleep", lambda _: None)


def make_client(handler):
    client = HHClient()
    transport = _http.build_transport(httpx2.MockTransport(handler))
    client._client = httpx2.Client(transport=transport)
    return client


def test_get_sends_a_single_get_request():
    requests = []

    def handler(request):
        requests.append(request.method)
        return httpx2.Response(200, json=[])

    assert make_client(handler)._get("cores") == []
    assert requests == ["GET"]


def test_get_retries_dropped_connections():
    requests = []

    def handler(request):
        requests.append(request.method)
        if len(requests) == 1:
            raise httpx2.RemoteProtocolError("dropped")
        return httpx2.Response(200, json=[{"code": "no2"}])

    assert make_client(handler)._get("cores") == [{"code": "no2"}]
    assert requests == ["GET", "GET"]
