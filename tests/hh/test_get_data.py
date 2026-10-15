import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from canairy.hh import HHClient
from canairy.hh._models import HHComponentDataParams, HHStationDataParams


def make_row(dt, component="no2_1h"):
    return {"datetime": dt, "station": "13ST", "component": component}


def make_params(start, end, timespan="custom"):
    return HHStationDataParams(
        period="1h", timespan=timespan, start=start, end=end, core=None
    )


def test_get_data_requests_windows_and_drops_shared_boundary(monkeypatch):
    client = HHClient()
    requests = []

    def fake_get(endpoint, params):
        requests.append((params.start, params.end))
        return [
            make_row(params.end.isoformat()),
            make_row(params.start.isoformat()),
        ]

    monkeypatch.setattr(client, "_get", fake_get)
    rows = client._get_data(
        "stations/13ST/data",
        make_params(datetime(2025, 1, 1), datetime(2025, 3, 15)),
        "1h",
    )
    assert requests == [
        (datetime(2025, 3, 4), datetime(2025, 3, 15)),
        (datetime(2025, 2, 1), datetime(2025, 3, 4)),
        (datetime(2025, 1, 1), datetime(2025, 2, 1)),
    ]
    assert [row["datetime"] for row in rows] == [
        "2025-03-15T00:00:00",
        "2025-03-04T00:00:00",
        "2025-02-01T00:00:00",
        "2025-01-01T00:00:00",
    ]


def test_get_data_keeps_rows_of_other_components(monkeypatch):
    client = HHClient()

    def fake_get(endpoint, params):
        ts = params.end.isoformat()
        return [make_row(ts, "no2_1h"), make_row(ts, "no_1h")]

    monkeypatch.setattr(client, "_get", fake_get)
    rows = client._get_data(
        "stations/13ST/data",
        make_params(datetime(2025, 1, 1), datetime(2025, 1, 2)),
        "1h",
    )
    assert len(rows) == 2


@pytest.fixture
def utc_host(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def berlin_now():
    return datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)


def test_get_data_splits_open_ended_range_up_to_now_in_berlin(monkeypatch, utc_host):
    client = HHClient()
    requests = []

    def fake_get(endpoint, params):
        requests.append((params.start, params.end))
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    before = berlin_now()
    client._get_data(
        "stations/13ST/data", make_params(datetime(2024, 1, 1), None), "1h"
    )
    assert len(requests) > 1
    assert before <= requests[0][1] <= berlin_now()
    assert requests[-1][0] == datetime(2024, 1, 1)


def test_get_data_splits_aware_start_with_open_end(monkeypatch):
    client = HHClient()
    requests = []

    def fake_get(endpoint, params):
        requests.append((params.start, params.end))
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    # e.g. the newest timestamp of a previous response
    start = datetime.fromisoformat("2024-01-01T00:00:00+01:00")
    client._get_data("stations/13ST/data", make_params(start, None), "1h")
    assert len(requests) > 1
    assert requests[-1][0] == datetime(2024, 1, 1)


def test_get_data_passes_through_non_custom_timespan(monkeypatch):
    client = HHClient()
    calls = []

    def fake_get(endpoint, params):
        calls.append(params)
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    client._get_data(
        "stations/13ST/data", make_params(None, None, timespan="lastyear"), "1h"
    )
    assert len(calls) == 1


def test_get_data_treats_range_without_timespan_as_custom(monkeypatch):
    client = HHClient()
    calls = []

    def fake_get(endpoint, params):
        calls.append(params)
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    params = HHComponentDataParams(start=datetime(2024, 1, 1), end=datetime(2024, 12, 31))
    client._get_data("components/no2_1h/data", params, "1h")
    assert len(calls) > 1
    assert all(call.timespan == "custom" for call in calls)


def test_get_data_rejects_range_with_non_custom_timespan(monkeypatch):
    client = HHClient()
    monkeypatch.setattr(client, "_get", lambda endpoint, params: [])
    with pytest.raises(ValueError, match="custom"):
        client._get_data(
            "stations/13ST/data",
            make_params(datetime(2024, 1, 1), None, timespan="lastyear"),
            "1h",
        )


@pytest.mark.parametrize("code", ["no2", "no2_1h_x"])
def test_get_component_data_rejects_custom_range_without_period(monkeypatch, code):
    client = HHClient()
    monkeypatch.setattr(client, "_get", lambda endpoint, params: [])
    with pytest.raises(ValueError, match="period"):
        client.get_component_data(code, start=datetime(2024, 1, 1))


@pytest.mark.parametrize("code", ["no2", "no2_1h_x"])
def test_get_component_data_without_range_needs_no_period(monkeypatch, code):
    client = HHClient()
    calls = []

    def fake_get(endpoint, params):
        calls.append(params)
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    client.get_component_data(code, timespan="lastday")
    assert len(calls) == 1


def test_get_component_data_period_suffix_ignores_case(monkeypatch):
    client = HHClient()
    calls = []

    def fake_get(endpoint, params):
        calls.append(params)
        return []

    monkeypatch.setattr(client, "_get", fake_get)
    client.get_component_data(
        "NO2_1H", start=datetime(2024, 1, 1), end=datetime(2024, 12, 31)
    )
    assert len(calls) > 1
