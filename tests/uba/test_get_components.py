import pytest

from canairy.uba import UBAClient
from canairy.uba.components import UBAComponentsGetResponse


def test_get_components(client):
    res = client.get_components()
    assert isinstance(res, UBAComponentsGetResponse)


def test_get_components_lang(client):
    res = client.get_components(lang="de")
    assert isinstance(res, UBAComponentsGetResponse)

    res = client.get_components(lang="en")
    assert isinstance(res, UBAComponentsGetResponse)


@pytest.fixture
def client():
    return UBAClient()
