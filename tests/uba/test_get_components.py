import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.components import ComponentsGetResponse


def test_get_components(client):
    res = client.get_components()
    assert isinstance(res, ComponentsGetResponse)

def test_get_components_lang(client):
    res = client.get_components(lang="de")
    assert isinstance(res, ComponentsGetResponse)

    res = client.get_components(lang="en")
    assert isinstance(res, ComponentsGetResponse)

def test_get_components_index(client):
    res = client.get_components(index="id")
    assert isinstance(res, ComponentsGetResponse)

    res = client.get_components(index="code")
    assert isinstance(res, ComponentsGetResponse)


@pytest.fixture
def client():
    return UBAClient()
