import httpx
import pytest

from canairy.be import BEClient
from canairy.hh import HHClient


@pytest.mark.parametrize(
    "cls, base_url",
    [
        (HHClient, "https://hamburg.luftmessnetz.de/api"),
        (BEClient, "https://luftdaten.berlin.de/api"),
    ],
)
def test_client_requests_its_network(cls, base_url):
    urls = []

    def handler(request):
        urls.append(str(request.url))
        return httpx.Response(200, json=[])

    client = cls()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    assert client.get_cores() == []
    assert urls == [f"{base_url}/cores"]
