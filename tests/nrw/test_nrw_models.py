from datetime import UTC, date, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest

from canairy import _http
from canairy.nrw import NRWClient, NRWMeasurement
from canairy.nrw._models import (
    CET,
    MEASUREMENT_COLUMNS,
    REFERENCE_MEASUREMENT_COLUMNS,
    TOTAL_AQI_COLUMNS,
    DatetimeMeasurementParams,
    Station,
    TotalAirQualityIndex,
)

HOURLY_ROW = [1, 3, 1, 1, 1, "2026-11-24 00:00:00", "2026-11-24 01:00:00", 21.597, 21.597, 10, 0]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(_http.time, "sleep", lambda _: None)


def make_client(handler) -> NRWClient:
    client = NRWClient()
    client._client = httpx2.Client(
        transport=_http.build_transport(httpx2.MockTransport(handler))
    )
    return client


def recording_client(body, status=200):
    requests: list[httpx2.Request] = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(status, json=body)

    return make_client(handler), requests


def query(request: httpx2.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlsplit(str(request.url)).query).items()}


# --- params ---------------------------------------------------------------------


def test_naive_datetimes_are_german_local_time_sent_as_cet():
    params = DatetimeMeasurementParams(
        komponente=[3, 200],
        beginn=datetime(2026, 7, 1, 0),  # CEST
        ende=datetime(2026, 12, 1, 0),  # CET
        station=1,
    )
    assert params.model_dump(exclude_none=True) == {
        "komponente": "3,200",
        "station": "1",
        "beginn": "2026-06-30T23:00",
        "ende": "2026-12-01T00:00",
    }


def test_aware_datetimes_are_converted_to_cet():
    params = DatetimeMeasurementParams(
        komponente=3,
        beginn=datetime(2026, 7, 1, 0, tzinfo=UTC),
        ende=datetime(2026, 7, 1, 2, tzinfo=CET),
    )
    dumped = params.model_dump(exclude_none=True)
    assert (dumped["beginn"], dumped["ende"]) == ("2026-07-01T01:00", "2026-07-01T02:00")


def test_get_hourly_request():
    client, requests = recording_client([HOURLY_ROW])
    client.get_hourly(3, datetime(2026, 11, 24), datetime(2026, 11, 24, 1), station=[1, 2])
    (request,) = requests
    assert request.url.path == "/api/stundenmittelwerte.php"
    assert query(request) == {
        "komponente": "3",
        "station": "1,2",
        "beginn": "2026-11-24T00:00",
        "ende": "2026-11-24T01:00",
    }


def test_get_daily_and_yearly_requests():
    client, requests = recording_client([])
    client.get_daily(200, date(2026, 11, 1), date(2026, 11, 3), method=1)
    client.get_yearly(3, [2024, 2025], matrix=1)
    assert query(requests[0]) == {
        "komponente": "200",
        "methode": "1",
        "beginn": "2026-11-01",
        "ende": "2026-11-03",
    }
    assert query(requests[1]) == {"komponente": "3", "matrix": "1", "jahr": "2024,2025"}


def test_get_stations_without_component_list_by_default():
    client, requests = recording_client([])
    client.get_stations(code=["AABU", "VACW"], station_class="Verkehr")
    assert query(requests[0]) == {
        "stationkuerzel": "AABU,VACW",
        "stationsklasse": "Verkehr",
        "komponentenliste": "nein",
    }


@pytest.mark.parametrize(
    ("start", "end", "error"),
    [
        (datetime(2026, 1, 1, 1), datetime(2026, 1, 1, 1), ValueError),
        (date(2026, 1, 2), date(2026, 1, 1), ValueError),
        (date(2026, 1, 1), datetime(2026, 1, 2), TypeError),
    ],
)
def test_invalid_ranges_raise_before_requesting(start, end, error):
    client, requests = recording_client([])
    with pytest.raises(error):
        client.get_hourly(3, start, end)
    assert requests == []


def test_total_aqi_needs_both_bounds():
    client, _ = recording_client([])
    with pytest.raises(ValueError, match="together"):
        client.get_total_air_quality_index(start=datetime(2026, 1, 1))


def test_availability_end_requires_start():
    client, _ = recording_client([])
    with pytest.raises(ValueError, match="start"):
        client.get_availability(end=date(2026, 1, 1))


# --- responses ------------------------------------------------------------------


def test_no_match_returns_empty_list():
    client, _ = recording_client({"fehler": {"text": "Keine passenden Einträge gefunden"}})
    assert client.get_hourly(999, datetime(2026, 1, 1), datetime(2026, 1, 2)) == []


def test_api_error_raises_value_error():
    body = {"fehler": {"text": "Ende Datum ist älter als Beginn Datum"}}
    client, _ = recording_client(body, status=422)
    with pytest.raises(ValueError, match="älter.*HTTP 422"):
        client.get_daily(3, date(2026, 1, 1), date(2026, 1, 2))


def test_server_error_raises_http_error():
    client, _ = recording_client(None, status=404)
    with pytest.raises(httpx2.HTTPStatusError):
        client.get_ozone_warnings()


def test_measurement_row():
    (m,) = NRWMeasurement.from_rows([HOURLY_ROW], MEASUREMENT_COLUMNS)
    assert (m.station, m.component, m.matrix, m.method, m.unit) == (1, 3, 1, 1, 1)
    assert m.start == datetime(2026, 11, 24, 0, tzinfo=CET)
    assert m.end - m.start == timedelta(hours=1)
    assert (m.value, m.raw_value, m.detection_limit) == (21.597, 21.597, 10)
    assert not m.below_detection_limit
    assert not m.validated
    assert m.reference is None


def test_summer_times_stay_in_cet():
    row = [1, 3, 1, 1, 1, "2026-07-01 00:00:00", "2026-07-02 00:00:00", 5, 5, 1, 1]
    (m,) = NRWMeasurement.from_rows([row], MEASUREMENT_COLUMNS)
    assert m.start.utcoffset() == timedelta(hours=1)
    assert (m.start.hour, m.end.hour) == (0, 0)
    assert m.validated


def test_value_below_detection_limit():
    row = [1, 3, 1, 1, 1, "2026-02-01 00:00:00", "2026-03-01 00:00:00", "2026-02",
           "<10", 8.6469, 10, 0]
    (m,) = NRWMeasurement.from_rows([row], REFERENCE_MEASUREMENT_COLUMNS)
    assert m.value is None
    assert m.below_detection_limit
    assert (m.raw_value, m.detection_limit, m.reference) == (8.6469, 10, "2026-02")


def test_unexpected_row_raises():
    with pytest.raises(ValueError, match="Unexpected row"):
        NRWMeasurement.from_rows([HOURLY_ROW[:-1]], MEASUREMENT_COLUMNS)
    with pytest.raises(ValueError, match="Unexpected row"):
        NRWMeasurement.from_rows(["Hinweis: Maximalanzahl erreicht"], MEASUREMENT_COLUMNS)


def test_total_aqi_row():
    row = [1, "2026-11-24 00:00:00", "2026-11-24 01:00:00", "2026-11-24 01:00:00",
           2, "gut", [3, 200], 0, 0, 0]
    (t,) = TotalAirQualityIndex.from_rows([row], TOTAL_AQI_COLUMNS)
    assert t.components == [3, 200]
    assert (t.index, t.text, t.ozone_substitute) == (2, "gut", False)


def test_station_with_components():
    item = {
        "mstkey": 1, "mstkrz": "AABU", "mstname": "Aachen-Burtscheid",
        "mstklasse": "Hintergrund", "mstumgebung": "städtisches Gebiet",
        "msteucode": None, "mstplz": 52066, "mststrasse": "Hein-Görgen-Straße",
        "mstort": "Aachen", "msthoehe": None, "mste32": 295020, "mstn32": 5626578,
        "mstbeschreibung": "…",
        "mstkomponenten": [
            {"kmpkey": 3, "matkey": 1, "metkey": 1, "einkey": 1, "aggkey": 1,
             "datenstart": "2019-12-31", "datenende": "2026-11-24"}
        ],
    }
    station = Station(**item)
    assert station.eu_code is None and station.altitude is None
    assert station.components is not None
    assert station.components[0].start == date(2019, 12, 31)
    assert station.components[0].unit == 1
