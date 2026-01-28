from datetime import datetime

import pytest

from air_pollution.uba import UBAClient
from air_pollution.uba.measures._models import UBAMeasuresGetResponse


def test_get_measures(client):
    start = datetime(2016, 1, 1, 0, 0, 0)
    stop = datetime(2016, 1, 2, 23, 0, 0)
    res = client.get_measures(start, stop, "DEHH070", 1, 2)
    assert isinstance(res, UBAMeasuresGetResponse)
    assert len(res.data) > 0


@pytest.fixture
def client():
    return UBAClient()
