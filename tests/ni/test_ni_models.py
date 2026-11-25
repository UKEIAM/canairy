import itertools
import json
from datetime import UTC, datetime, timedelta

import httpx2
import pytest

from canairy import _http
from canairy.ni import NIClient, NIData, NIStation
from canairy.ni._models import BERLIN, parse_timestamp


def make_feed(
    *, datum="25.11.2026", zeit="10:00", zeitzone="UTC+1h", verlauf=None
) -> dict:
    return {
        "Dateihistorie": ["21.09.2026-SK: verlauf_indexwerte entfernt"],
        "messnetz": "Lufthygienisches Überwachungssystem Niedersachsen  (LÜN)",
        "datum": datum,
        "zeit": zeit,
        "zeitzone": zeitzone,
        "bezugsquelle": {"amt": "Staatliches Gewerbeaufsichtsamt Hildesheim"},
        "kommentar": ["BITTE BEACHTEN: vorläufig"],
        "komponenten": [
            {
                "kennung": "NO2",
                "name": "Stickstoffdioxid",
                "einheit": "µg/m³",
                "zeitbezug": "Einstundenmittelwert",
            },
            {
                "kennung": "TT",
                "name": "Temperatur",
                "einheit": "°C",
                "zeitbezug": "Einstundenmittelwert",
            },
        ],
        "stationen": [
            {
                "kennung": "BGSW",
                "EOI-Kennung": "DENI011",
                "name": "Braunschweig",
                "ort": "Braunschweig/Broitzem",
                "strasse": "Broitzem (Fernmeldeturm)",
                "koordinaten": {"breite": "52,22694", "laenge": "10,47364"},
                "hoehe": "98",
                "gebiet": "vorstädtisch",
                "art": "Hintergrund",
                "repraesentativitaet": "Stadtgebiet Braunschweig",
            }
        ],
        "messwerte": [
            {
                "kennung": "BGSW",
                "messstellen": [
                    {
                        "kennung": "NO2",
                        "luftqualitaet": "1,25",
                        "verlauf": verlauf or ["14", "***", "<2"],
                    },
                    {"kennung": "TT", "verlauf": ["-1,5", "0,3", "2,0"]},
                ],
            }
        ],
    }


@pytest.fixture
def data() -> NIData:
    return NIData.from_response(make_feed())


def test_metadata(data):
    assert data.network.startswith("Lufthygienisches")
    assert data.timestamp == datetime(2026, 11, 25, 10, tzinfo=BERLIN)
    assert data.comments and data.history
    assert [c.code for c in data.components] == ["NO2", "TT"]
    assert data.components[0].unit == "µg/m³"


def test_station_numbers_use_decimal_comma(data):
    (station,) = data.stations
    assert isinstance(station, NIStation)
    assert (station.code, station.code_eu) == ("BGSW", "DENI011")
    assert (station.lat, station.lng, station.altitude) == (52.22694, 10.47364, 98)
    assert (station.area, station.type) == ("vorstädtisch", "Hintergrund")


def test_values_end_at_timestamp_hourly_oldest_first(data):
    values = data.get_series("BGSW", "NO2").values
    assert [v.datetime for v in values] == [
        data.timestamp - timedelta(hours=h) for h in (2, 1, 0)
    ]


def test_missing_and_below_limit_values(data):
    no2 = data.get_series("BGSW", "NO2")
    assert [(v.value, v.detection_limit) for v in no2.values] == [
        (14.0, None),
        (None, None),
        (None, 2.0),
    ]
    tt = data.get_series("BGSW", "TT")
    assert [v.value for v in tt.values] == [-1.5, 0.3, 2.0]


def test_air_quality(data):
    assert data.get_series("BGSW", "NO2").air_quality == 1.25
    assert data.get_series("BGSW", "TT").air_quality is None


def documented_format(feed: dict) -> dict:
    """Convert to the documented format: verlauf_stundenwerte/_indexwerte."""
    for station in feed["messwerte"]:
        for item in station["messstellen"]:
            item["verlauf_stundenwerte"] = item.pop("verlauf")
            if item.pop("luftqualitaet", None) is not None:
                item["verlauf_indexwerte"] = ["1,4", "***", "1,25"]
    return feed


def test_documented_format_with_index_history():
    data = NIData.from_response(documented_format(make_feed()))
    no2 = data.get_series("BGSW", "NO2")
    assert [v.value for v in no2.values] == [14.0, None, None]
    assert [v.air_quality for v in no2.values] == [1.4, None, 1.25]
    assert no2.air_quality == 1.25  # the newest index value
    tt = data.get_series("BGSW", "TT")
    assert [v.value for v in tt.values] == [-1.5, 0.3, 2.0]
    assert tt.air_quality is None
    assert all(v.air_quality is None for v in tt.values)


def test_documented_format_missing_current_index():
    feed = documented_format(make_feed())
    feed["messwerte"][0]["messstellen"][0]["verlauf_indexwerte"][-1] = "***"
    assert NIData.from_response(feed).get_series("BGSW", "NO2").air_quality is None


def test_index_history_length_mismatch_raises():
    feed = documented_format(make_feed())
    feed["messwerte"][0]["messstellen"][0]["verlauf_indexwerte"].pop()
    with pytest.raises(ValueError, match="index values"):
        NIData.from_response(feed)


def test_series_without_values_raises():
    feed = make_feed()
    del feed["messwerte"][0]["messstellen"][1]["verlauf"]
    with pytest.raises(ValueError, match="No values"):
        NIData.from_response(feed)


def test_air_quality_zero_means_no_current_value():
    feed = make_feed()
    feed["messwerte"][0]["messstellen"][0]["luftqualitaet"] = "0,00"
    assert NIData.from_response(feed).get_series("BGSW", "NO2").air_quality is None


def test_get_series_unknown_raises(data):
    with pytest.raises(KeyError):
        data.get_series("BGSW", "O3")


def test_summer_time_offset():
    ts = parse_timestamp("01.07.2026", "14:00", "UTC+2h")
    assert ts == datetime(2026, 7, 1, 14, tzinfo=BERLIN)
    assert ts.utcoffset() == timedelta(hours=2)


def test_unknown_zone_raises():
    with pytest.raises(ValueError, match="time zone"):
        parse_timestamp("01.07.2026", "14:00", "MESZ")


def test_series_across_dst_end_stays_hourly():
    # DST ended 25.10.2026 03:00 CEST -> 02:00 CET; 03:00 CET is 4 h after
    # 00:00 CEST.
    feed = make_feed(
        datum="25.10.2026", zeit="03:00", verlauf=["1", "2", "3", "4", "5"]
    )
    values = NIData.from_response(feed).get_series("BGSW", "NO2").values
    assert values[0].datetime == datetime(2026, 10, 25, 0, tzinfo=BERLIN)
    assert values[0].datetime.utcoffset() == timedelta(hours=2)
    assert values[-1].datetime.utcoffset() == timedelta(hours=1)
    # Aware datetimes in the same zone subtract by wall time; compare in UTC.
    utc = [v.datetime.astimezone(UTC) for v in values]
    assert all(b - a == timedelta(hours=1) for a, b in itertools.pairwise(utc))


def test_client_decodes_latin1():
    requests = []

    def handler(request):
        requests.append(str(request.url))
        body = json.dumps(make_feed(), ensure_ascii=False).encode("latin-1")
        return httpx2.Response(200, content=body, headers={"content-type": "text/plain"})

    client = NIClient()
    client._client = httpx2.Client(
        transport=_http.build_transport(httpx2.MockTransport(handler))
    )
    data = client.get_data()
    assert requests == [NIClient.URL]
    assert data.stations[0].area == "vorstädtisch"
    assert data.network.endswith("(LÜN)")
