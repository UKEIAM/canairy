import pytest

from air_pollution.uba import UBAClient


def test_get_stations(client):
    client.get_components()
    client.get_components(lang="de")
    client.get_components(lang="en")
    client.get_components(index="id")
    client.get_components(index="code")


@pytest.fixture
def client():
    return UBAClient()
