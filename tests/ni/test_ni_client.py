from datetime import timedelta

from canairy.ni import NIClient, NIData


def test_get_data():
    data = NIClient().get_data()
    assert isinstance(data, NIData)
    assert data.stations and data.components and data.series

    station_codes = {s.code for s in data.stations}
    component_codes = {c.code for c in data.components}
    assert {s.station for s in data.series} <= station_codes
    assert {s.component for s in data.series} <= component_codes
    assert all(s.code_eu.startswith("DENI") for s in data.stations)

    # 30 days of hourly values, ending at the feed timestamp.
    for series in data.series:
        assert len(series.values) == 30 * 24
        assert series.values[-1].datetime == data.timestamp
        assert series.values[0].datetime == data.timestamp - timedelta(hours=719)
