import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.scopes import UBAScopesGetResponse


def test_get_scopes(client):
    res = client.get_scopes()
    assert isinstance(res, UBAScopesGetResponse)


def test_get_scopes_lang(client):
    res = client.get_scopes(lang="de")
    assert isinstance(res, UBAScopesGetResponse)

    res = client.get_scopes(lang="en")
    assert isinstance(res, UBAScopesGetResponse)


@pytest.fixture
def client():
    return UBAClient()
