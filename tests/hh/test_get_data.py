from datetime import datetime

from canairy.hh import HHClient
from canairy.hh._models import HHStationDataParams


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
