from datetime import datetime

import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.measures._models import MeasuresGetResponse


def test_get_measures(client):
    start = datetime(2025, 1, 1, 0, 0, 0)
    stop = datetime(2025, 1, 2, 0, 0, 0)
    res = client.get_measures(start, stop, 1, 1)
    assert isinstance(res, MeasuresGetResponse)


@pytest.fixture
def client():
    return UBAClient()
