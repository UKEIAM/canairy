from datetime import datetime, timedelta, timezone

from canairy.hh._models import BERLIN, HHComponentDataParams


def test_aware_range_is_converted_to_naive_berlin_time():
    params = HHComponentDataParams(
        start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 7, 1, 12, tzinfo=timezone(timedelta(hours=2))),
    )
    assert params.start == datetime(2025, 1, 1, 1)
    assert params.end == datetime(2025, 7, 1, 12)
    assert params.model_dump(exclude_none=True) == {
        "start": "01.01.2025 01:00",
        "end": "01.07.2025 12:00",
    }


def test_naive_range_is_kept_as_berlin_time():
    params = HHComponentDataParams(
        start=datetime(2025, 1, 1), end=datetime(2025, 1, 2, tzinfo=BERLIN)
    )
    assert params.start == datetime(2025, 1, 1)
    assert params.end == datetime(2025, 1, 2)
