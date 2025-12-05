import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.scopes import ScopesGetResponse


def test_get_scopes(client):
    res = client.get_scopes()
    assert isinstance(res, ScopesGetResponse)

def test_get_scopes_lang(client):
    res = client.get_scopes(lang="de")
    assert isinstance(res, ScopesGetResponse)

    res = client.get_scopes(lang="en")
    assert isinstance(res, ScopesGetResponse)

def test_get_scopes_index(client):
    res = client.get_scopes(index="id")
    assert isinstance(res, ScopesGetResponse)

    res = client.get_scopes(index="code")
    assert isinstance(res, ScopesGetResponse)


@pytest.fixture
def client():
    return UBAClient()
