from datetime import datetime

import pytest

from canairy.uba import UBAClient
from canairy.uba.measures import UBAMeasuresLimitsGetResponse
from canairy.uba.measures._models import UBAMeasuresGetResponse


def test_get_measures(client):
    start = datetime(2016, 1, 1, 0, 0, 0)
    stop = datetime(2016, 1, 2, 23, 0, 0)
    res = client.get_measures(start, stop, "DEHH070", 1, 2)
    assert isinstance(res, UBAMeasuresGetResponse)
    assert len(res.data) > 0


@pytest.fixture
def client():
    return UBAClient()


def test_get_measures_limits(client):
    res = client.get_measures_limits()
    assert isinstance(res, UBAMeasuresLimitsGetResponse)
    assert len(res.data) > 0
    assert all(lim.date_start_min <= lim.date_start_max for lim in res.data)
