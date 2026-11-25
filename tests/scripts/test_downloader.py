import datetime
import pickle
from types import SimpleNamespace

from canairy.scripts.downloader import download_multi_station
from canairy.uba.measures import UBAMeasuresLimit, UBAMeasuresLimitsGetResponse


class FakeClient:
    """Station 1 has NO2 (5/2) 2019-2020 only; station 2 has no data at all."""

    def __init__(self):
        self.measures_calls = []

    def get_measures_limits(self):
        lim = UBAMeasuresLimit(
            scope_id=2,
            component_id=5,
            station_id=1,
            date_start_min=datetime.datetime(2019, 6, 1),
            date_start_max=datetime.datetime(2020, 12, 31, 23),
        )
        return UBAMeasuresLimitsGetResponse(indices=[], data=[lim])

    def get_stations(self):
        stations = [SimpleNamespace(id=1, code="ST1"), SimpleNamespace(id=2, code="ST2")]
        return SimpleNamespace(data=stations)

    def get_measures(self, start, end, station, component, scope):
        self.measures_calls.append((start.year, station, component, scope))
        return SimpleNamespace(model_dump=lambda mode: {"station": station})


def test_skips_combinations_without_data(tmp_path, monkeypatch):
    fake_datetime = SimpleNamespace(
        datetime=datetime.datetime,
        date=SimpleNamespace(today=lambda: datetime.date(2022, 5, 1)),
    )
    monkeypatch.setattr("canairy.scripts.downloader.datetime", fake_datetime)
    client = FakeClient()

    download_multi_station(client, year_start=2018, outpath=tmp_path)

    assert client.measures_calls == [(2019, 1, 5, 2), (2020, 1, 5, 2)]
    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.pkl"))
    assert files == ["2019/ST1/NO2_2.pkl", "2020/ST1/NO2_2.pkl"]
    with (tmp_path / "2019/ST1/NO2_2.pkl").open("rb") as f:
        assert pickle.load(f) == {"station": 1}
