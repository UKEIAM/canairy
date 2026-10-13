import itertools
from datetime import datetime

import pytest

from canairy.hh import HHClient
from canairy.hh._models import (
    HHCore,
    HHStation,
    HHStationData,
    HHThreshold,
)


def test_get_components(client):
    res = client.get_components()
    assert isinstance(res, list)
    assert res != []


def test_get_components_data(client):
    test_query = {
        "code": "no2_1h",
        "timespan": "custom",
        "start": datetime(2025, 1, 2, 9),
        "end": datetime(2025, 1, 3, 10),
    }
    res = client.get_component_data(**test_query)
    assert isinstance(res, list)
    assert res != []


def test_get_cores(client):
    res = client.get_cores()
    assert isinstance(res, list)
    assert all(isinstance(item, HHCore) for item in res)


def test_get_thresholds(client):
    res = client.get_thresholds()
    assert isinstance(res, list)
    assert all(isinstance(item, HHThreshold) for item in res)


def test_get_stations(client):
    vals = (None, True, False)
    for active, hidden in itertools.product(vals, vals):
        test_query = {"active": active, "include_hidden": hidden}
        res = client.get_stations(**test_query)
        assert isinstance(res, list)
        assert all(isinstance(item, HHStation) for item in res)


def test_get_station(client):
    test_query = {"code": "80kt"}
    res = client.get_station(**test_query)
    assert isinstance(res, HHStation)


def test_get_station_data(client):
    test_query = {
        "station_code": "80kt",
        "period": "1h",
        "timespan": "custom",
        "start": datetime(2025, 1, 2, 9),
        "end": datetime(2025, 1, 5, 10),
    }
    res = client.get_station_data(**test_query)
    assert isinstance(res, list)
    assert all(isinstance(item, HHStationData) for item in res)


@pytest.fixture
def client():
    return HHClient()
