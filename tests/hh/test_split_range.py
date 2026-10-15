import itertools
from datetime import datetime, timedelta

import pytest

from canairy.hh._client import RANGE_LIMITS, split_range


def test_range_within_limit_is_not_split():
    start, end = datetime(2025, 1, 1), datetime(2025, 2, 1)
    assert split_range(start, end, "1h") == [(start, end)]


def test_range_exceeding_limit_is_split():
    start, end = datetime(2025, 1, 1), datetime(2025, 3, 15, 12)
    assert split_range(start, end, "1h") == [
        (datetime(2025, 1, 1), datetime(2025, 2, 1)),
        (datetime(2025, 2, 1), datetime(2025, 3, 4)),
        (datetime(2025, 3, 4), datetime(2025, 3, 15, 12)),
    ]


@pytest.mark.parametrize("period", sorted(RANGE_LIMITS))
def test_windows_are_contiguous_and_within_limit(period):
    start, end = datetime(2016, 1, 1), datetime(2025, 12, 31, 23)
    windows = split_range(start, end, period)
    assert windows[0][0] == start
    assert windows[-1][1] == end
    assert all(a[1] == b[0] for a, b in itertools.pairwise(windows))
    assert all(e - s <= RANGE_LIMITS[period] for s, e in windows)


def test_unlimited_period_is_not_split():
    start, end = datetime(1984, 1, 1), datetime(2025, 1, 1)
    assert split_range(start, end, "1m") == [(start, end)]


def test_daily_year_is_one_window():
    start = datetime(2024, 1, 1)
    end = start + timedelta(days=365)
    assert split_range(start, end, "24h") == [(start, end)]
