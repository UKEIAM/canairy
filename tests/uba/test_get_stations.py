import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba._models import Station, UBAStationGetResponse


def test_get_stations(client):
    res = client.get_stations()
    assert isinstance(res, UBAStationGetResponse)
    assert isinstance(res.data, list)
    for item in res.data:
        assert isinstance(item, Station)


@pytest.fixture
def client():
    return UBAClient()
