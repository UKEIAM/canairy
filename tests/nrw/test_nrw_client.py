from datetime import date, datetime, timedelta

import pytest

from canairy.nrw import (
    NRWAggregation,
    NRWClient,
    NRWComponent,
    NRWMeasurement,
    NRWOzoneWarning,
    NRWStation,
    NRWTotalAirQualityIndex,
)

AACHEN_BURTSCHEID = 1
NO2, O3, PM10 = 3, 1, 200


def test_metadata(client):
    components = client.get_components()
    assert all(isinstance(c, NRWComponent) for c in components)
    assert {(c.id, c.code) for c in components} >= {(1, "O3"), (3, "NO2"), (200, "PM10")}
    assert all(isinstance(a, NRWAggregation) for a in client.get_aggregations())
    assert client.get_methods() and client.get_matrices() and client.get_units()
    assert "Verkehr" in client.get_station_classes()
    assert client.get_station_environments()


def test_get_stations_by_eu_code_with_components(client):
    (station,) = client.get_stations(eu_code="DENW094", include_components=True)
    assert isinstance(station, NRWStation)
    assert station.id == AACHEN_BURTSCHEID
    assert station.components
    assert any(c.component == NO2 and c.aggregation == 1 for c in station.components)


def test_get_availability(client):
    res = client.get_availability(station=AACHEN_BURTSCHEID, component=NO2)
    assert res and all(a.station == AACHEN_BURTSCHEID for a in res)


def test_get_hourly_across_dst_start(client):
    # Naive times are German local time: 00:00 CET to 04:00 CEST is 3 hours.
    res = client.get_hourly(
        NO2, datetime(2026, 3, 29), datetime(2026, 3, 29, 4), station=AACHEN_BURTSCHEID
    )
    assert all(isinstance(m, NRWMeasurement) for m in res)
    assert [m.end - m.start for m in res] == [timedelta(hours=1)] * 3
    assert any(m.below_detection_limit for m in res)


def test_get_daily_end_is_exclusive(client):
    res = client.get_daily(
        PM10, date(2026, 11, 1), date(2026, 11, 3), station=AACHEN_BURTSCHEID
    )
    assert [m.start.date() for m in res] == [date(2026, 11, 1), date(2026, 11, 2)]


def test_get_monthly_and_yearly_have_reference(client):
    monthly = client.get_monthly(
        NO2, date(2026, 1, 1), date(2026, 3, 1), station=AACHEN_BURTSCHEID
    )
    assert [m.reference for m in monthly] == ["2026-01", "2026-02"]
    yearly = client.get_yearly(NO2, [2024, 2025], station=AACHEN_BURTSCHEID)
    assert [m.reference for m in yearly] == ["2024", "2025"]


def test_no_match_is_empty(client):
    assert client.get_hourly(999, datetime(2026, 1, 1), datetime(2026, 1, 2)) == []


def test_indices_and_warnings(client):
    aqi = client.get_air_quality_index(
        [NO2, PM10], datetime(2026, 11, 24), datetime(2026, 11, 24, 2),
        station=AACHEN_BURTSCHEID,
    )
    assert {a.component for a in aqi} <= {NO2, PM10}
    total = client.get_total_air_quality_index(station=AACHEN_BURTSCHEID)
    assert all(isinstance(t, NRWTotalAirQualityIndex) for t in total)
    warnings = client.get_ozone_warnings()
    assert warnings and all(isinstance(w, NRWOzoneWarning) for w in warnings)
    assert client.get_pm10_exceedance_days(2025, station=AACHEN_BURTSCHEID)


@pytest.fixture
def client():
    return NRWClient()
