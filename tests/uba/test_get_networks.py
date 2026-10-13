import pytest

from canairy.uba import UBAClient
from canairy.uba.networks import UBANetworksGetResponse


def test_get_networks(client):
    res = client.get_networks()
    assert isinstance(res, UBANetworksGetResponse)


def test_get_networks_lang(client):
    res = client.get_networks(lang="de")
    assert isinstance(res, UBANetworksGetResponse)

    res = client.get_networks(lang="en")
    assert isinstance(res, UBANetworksGetResponse)


@pytest.fixture
def client():
    return UBAClient()
