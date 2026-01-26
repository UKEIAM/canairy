import datetime
import random
import string

import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.utils import (
    filter_stations_active,
    filter_stations_by_network,
    unpack,
)


def test_unpack_depth(indices_ok):
    assert unpack(indices_ok) == ["a", "B", 2, 3.14]


def test_unpack_raises(indices_bad):
    with pytest.raises(TypeError):
        unpack(indices_bad)


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


@pytest.fixture
def indices_ok():
    depth = random.randint(1, 20)
    keys = random.choices(string.ascii_letters, k=depth)
    return nested_indices({}, keys, target=["a", "B", 2, 3.14])


@pytest.fixture
def indices_bad():
    depth = random.randint(1, 20)
    keys = random.choices(string.ascii_letters, k=depth)
    return nested_indices({}, keys, target="THIS IS BAD!")


def nested_indices(out, keys, target):
    if len(keys) == 1:
        out[keys.pop()] = target
        return out
    else:
        k = keys.pop()
        out[k] = {}
        nested_indices(out[k], keys, target=target)
        return out
