import datetime
import random

import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.utils import filter_stations_active, filter_stations_by_network


def test_filter_stations_by_network(stations, networks):
    query = {
        "id": random.choice(stations).id,
        "code": random.choice(stations).code,
        "name": random.choice(stations).name,
    }

    for key, val in query.items():
        assert _check(stations, networks, key, val)


def _check(stations, networks, key, val):
    return all(
        getattr(s, key) == val
        for s in filter_stations_by_network(stations, networks, val)
    )


def test_filter_station_active(stations):
    q_from = datetime.date(1999, 4, 3)
    q_to = datetime.date(2016, 11, 6)

    res = filter_stations_active(stations, q_from, q_to)

    for station in res:
        a = station.active_from <= q_from
        b = True if station.active_to is None else station.active_to >= q_to
        assert a and b


@pytest.fixture
def networks(client):
    return client.get_networks().data


@pytest.fixture
def stations(client):
    return client.get_stations("measure").data


@pytest.fixture
def client():
    return UBAClient()
