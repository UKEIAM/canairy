import random

import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.utils import filter_stations_by_network


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


@pytest.fixture
def networks(client):
    return client.get_networks().data


@pytest.fixture
def stations(client):
    return client.get_stations("measure").data


@pytest.fixture
def client():
    return UBAClient()
