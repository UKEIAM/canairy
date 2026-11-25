import httpx2
import pytest

from canairy import _http
from canairy.uba import UBAClient


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(_http.time, "sleep", lambda _: None)


def make_client(statuses):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        status = statuses[min(len(requests), len(statuses)) - 1]
        return httpx2.Response(status, json={"ok": status})

    client = UBAClient()
    transport = _http.build_transport(
        httpx2.MockTransport(handler), _http.UBA_RETRY_STATUSES
    )
    client._client = httpx2.Client(transport=transport)
    return client, requests


@pytest.mark.parametrize("error", [429, 503])
def test_get_retries_transient_errors(error):
    client, requests = make_client([error, 200])
    assert client._get("scopes") == {"ok": 200}
    assert requests == [f"{UBAClient.BASE_URL}/scopes/json"] * 2


def test_get_raises_client_errors_at_once():
    client, requests = make_client([404])
    with pytest.raises(httpx2.HTTPStatusError):
        client._get("scopes")
    assert len(requests) == 1


def test_get_raises_once_retries_are_exhausted():
    client, requests = make_client([503])
    with pytest.raises(httpx2.HTTPStatusError):
        client._get("scopes")
    assert len(requests) == _http.MAX_RETRIES
