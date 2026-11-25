from datetime import UTC, datetime, timedelta, timezone

import pytest

from canairy._luftmessnetz._models import (
    BERLIN,
    ComponentData,
    ComponentDataParams,
    Station,
    StationData,
)


@pytest.mark.parametrize("model", [StationData, ComponentData])
def test_data_rows_accept_null_and_float_values(model):
    row = {
        "datetime": "2025-01-01T01:00:00+01:00",
        "station": "13ST",
        "core": "no2",
        "component": "no2_1h",
        "period": "1h",
    }
    res = model.from_response([{**row, "value": None}, {**row, "value": 12.5}])
    assert [item.value for item in res] == [None, 12.5]


def test_aware_range_is_converted_to_naive_berlin_time():
    params = ComponentDataParams(
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 7, 1, 12, tzinfo=timezone(timedelta(hours=2))),
    )
    assert params.start == datetime(2025, 1, 1, 1)
    assert params.end == datetime(2025, 7, 1, 12)
    assert params.model_dump(exclude_none=True) == {
        "start": "01.01.2025 01:00",
        "end": "01.07.2025 12:00",
    }


def test_naive_range_is_kept_as_berlin_time():
    params = ComponentDataParams(
        start=datetime(2025, 1, 1), end=datetime(2025, 1, 2, tzinfo=BERLIN)
    )
    assert params.start == datetime(2025, 1, 1)
    assert params.end == datetime(2025, 1, 2)


def test_station_accepts_missing_metadata():
    # Berlin lists virtual and internal stations without EU code, address,
    # coordinates, measuring start or URL.
    station = Station.from_response([{
        "name": "Verkehr",
        "code": "vir-v",
        "codeEu": None,
        "address": None,
        "lat": None,
        "lng": None,
        "active": True,
        "stationgroups": ["traffic"],
        "measuringStart": None,
        "measuringEnd": None,
        "measuringHeight": None,
        "url": None,
        "information": None,
        "components": [],
        "activeComponents": [],
        "partials": [],
        "lqis": [],
        "exceeds": [],
    }])[0]
    assert station.code_eu is None
    assert station.measuring_start is None


def test_data_rows_accept_twelve_month_moving_mean():
    row = {
        "datetime": "2026-10-01T00:00:00+02:00",
        "station": "mc014",
        "core": "no2",
        "component": "no2_12mg",
        "period": "12mg",
        "value": 20.0,
    }
    assert ComponentData.from_response([row])[0].period == "12mg"
