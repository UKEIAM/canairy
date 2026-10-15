import pytest

from canairy.uba import UBAClient
from canairy.uba.thresholds import UBAThresholdsGetResponse


def test_get_thresholds_use(client):
    res = client.get_thresholds(use="airquality", component_id=1, scope_id=2)
    assert isinstance(res, UBAThresholdsGetResponse)

    res = client.get_thresholds(use="measure", component_id=1, scope_id=2)
    assert isinstance(res, UBAThresholdsGetResponse)


@pytest.fixture
def client():
    return UBAClient()
