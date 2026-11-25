import datetime

import pytest

from canairy.uba.measures import UBAMeasuresLimit, UBAMeasuresLimitsGetResponse

INDICES = [
    "scope id",
    "component id",
    "station id",
    "limit date start min",
    "limit date start max",
]


def _response(indices=INDICES):
    return {
        "request": {"recent": False, "index": "id", "lang": "en"},
        "indices": {"combination of scope id, component id, station id": indices},
        "data": {
            "257": ["2", "5", "7", "2016-01-01 00:00:00", "2021-01-18 12:00:00"],
            "4231": ["4", "2", "31", "2019-03-01 00:00:00", "2026-11-25 07:00:00"],
        },
    }


def test_from_response():
    res = UBAMeasuresLimitsGetResponse.from_response(_response())
    assert res.indices == INDICES
    assert res.data[0] == UBAMeasuresLimit(
        scope_id=2,
        component_id=5,
        station_id=7,
        date_start_min=datetime.datetime(2016, 1, 1),
        date_start_max=datetime.datetime(2021, 1, 18, 12),
    )


def test_from_response_rejects_column_drift():
    with pytest.raises(ValueError, match="column order"):
        UBAMeasuresLimitsGetResponse.from_response(_response(INDICES[::-1]))


def test_lookup():
    lookup = UBAMeasuresLimitsGetResponse.from_response(_response()).lookup()
    assert set(lookup) == {(7, 5, 2), (31, 2, 4)}


@pytest.mark.parametrize(
    ("year", "expected"),
    [(2018, False), (2019, True), (2021, True), (2022, False)],
)
def test_overlaps(year, expected):
    lim = UBAMeasuresLimit(
        scope_id=2,
        component_id=5,
        station_id=7,
        date_start_min=datetime.datetime(2019, 12, 31, 23),
        date_start_max=datetime.datetime(2021, 1, 1, 0),
    )
    start = datetime.datetime(year, 1, 1)
    end = datetime.datetime(year, 12, 31, 23)
    assert lim.overlaps(start, end) is expected
