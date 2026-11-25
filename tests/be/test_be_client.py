import itertools
from datetime import datetime, timedelta

import pytest

from canairy.be import (
    BEClient,
    BEComponent,
    BEComponentData,
    BECore,
    BEStation,
    BEStationData,
    BEThreshold,
)


def test_get_components(client):
    res = client.get_components()
    assert res != []
    assert all(isinstance(item, BEComponent) for item in res)


def test_get_cores(client):
    res = client.get_cores()
    assert res != []
    assert all(isinstance(item, BECore) for item in res)


def test_get_thresholds(client):
    res = client.get_thresholds()
    assert res != []
    assert all(isinstance(item, BEThreshold) for item in res)


def test_get_stations_includes_stations_without_eu_code(client):
    res = client.get_stations(include_hidden=True)
    assert all(isinstance(item, BEStation) for item in res)
    assert any(item.code_eu is None for item in res)


def test_get_station(client):
    res = client.get_station("mc010")
    assert res.code_eu == "DEBE010"


def test_get_station_data_lastday(client):
    res = client.get_station_data("mc010", period="1h", timespan="lastday")
    assert res != []
    assert all(isinstance(item, BEStationData) for item in res)


def test_get_station_data_long_range_is_not_truncated(client):
    start, end = datetime(2025, 1, 1), datetime(2025, 3, 31, 23)
    res = client.get_station_data(
        "mc174", period="1h", timespan="custom", start=start, end=end, core="no2"
    )
    timestamps = [item.datetime for item in res if item.component == "no2_1h"]
    assert timestamps[0].replace(tzinfo=None) == end
    assert timestamps[-1].replace(tzinfo=None) == start
    assert all(a - b == timedelta(hours=1) for a, b in itertools.pairwise(timestamps))


def test_get_component_data_long_range_is_not_truncated(client):
    start, end = datetime(2024, 1, 1), datetime(2025, 6, 30)
    res = client.get_component_data(
        "pm10_24h", timespan="custom", start=start, end=end
    )
    assert all(isinstance(item, BEComponentData) for item in res)
    timestamps = sorted({item.datetime.replace(tzinfo=None) for item in res})
    days = (end - start).days + 1
    assert timestamps == [start + timedelta(days=i) for i in range(days)]


def test_get_component_data_twelve_month_moving_mean(client):
    res = client.get_component_data(
        "no2_12mg",
        timespan="custom",
        start=datetime(2024, 1, 1),
        end=datetime(2024, 12, 1),
    )
    assert {item.period for item in res} == {"12mg"}


@pytest.fixture
def client():
    return BEClient()
