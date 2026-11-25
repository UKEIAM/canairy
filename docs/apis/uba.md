# Umweltbundesamt (UBA)

| | |
|---|---|
| Module | `canairy.uba` (`UBAClient`) |
| Network | [Umweltbundesamt](https://luftdaten.umweltbundesamt.de), federal collection of all state networks |
| API | `https://luftdaten.umweltbundesamt.de/api/air-data/v4`, URLs are `{BASE_URL}/{endpoint}/json` |
| Coverage | all of Germany (~2,400 stations, incl. closed ones), measurements from 2016-01-01 |

## Usage

```python
from datetime import datetime

from canairy.uba import UBAClient

uba = UBAClient()

# Hourly NO₂ at Hamburg-Sternschanze (DEHH008), 1 January 2024, 00:00–05:00
res = uba.get_measures(
    datetime(2024, 1, 1, 0),
    datetime(2024, 1, 1, 5),  # inclusive
    station="DEHH008",        # station code or numeric id
    component=5,              # NO2
    scope=2,                  # one-hour average
)

for m in res.data:
    print(m.date_start, m.value, m.index)
# 2024-01-01 00:00:00 45.0 2
# 2024-01-01 01:00:00 33.0 1
# ...
```

| Method | Endpoint | Returns |
|---|---|---|
| `get_stations(usage=, dt_start=, dt_stop=, lang=)` | `stations` | `UBAStationGetResponse` |
| `get_networks(lang=)` | `networks` | `UBANetworksGetResponse` |
| `get_components(lang=)` | `components` | `UBAComponentsGetResponse` |
| `get_scopes(lang=)` | `scopes` | `UBAScopesGetResponse` |
| `get_measures(dt_start, dt_stop, station, component, scope)` | `measures` | `UBAMeasuresGetResponse` |
| `get_measures_limits()` | `measureslimits` | `UBAMeasuresLimitsGetResponse` |
| `get_thresholds(use, component_id, scope_id)` | `thresholds` | `UBAThresholdsGetResponse` |

Each response model has a `data` list. Pass `lang="en"` for English names; the default is
German.

### Components and scopes

Components (pollutants) and scopes (averaging types) are numeric ids. Look them up with the
metadata endpoints:

```python
for c in uba.get_components(lang="en").data:
    print(c.id, c.code, c.unit, c.name)
# 1 PM10 µg/m³ Particulate matter
# 3 O3 µg/m³ Ozone
# 5 NO2 µg/m³ Nitrogen dioxide
# 9 PM2 µg/m³ Particulate matter  ← PM2.5
# ...

for s in uba.get_scopes(lang="en").data:
    print(s.id, s.code, s.name)
# 1 1TMW Daily average
# 2 1SMW One hour average
# ...
```

### Stations

```python
from canairy.uba.utils import filter_stations_active, filter_stations_by_network

stations = uba.get_stations(lang="en").data        # ~2,400 stations, incl. closed ones
networks = uba.get_networks(lang="en").data

hamburg = filter_stations_by_network(stations, networks, "HH")
running = filter_stations_active(hamburg, "2020-01-01", "2024-12-31")
```

- `filter_stations_by_network` matches the network by any of its fields, e.g. the state code
  (`"HH"`, case insensitive) or its id.
- `filter_stations_active` keeps stations active during the whole period.

### Data availability

`get_measures_limits()` returns the first and last measurement start for every
scope × component × station combination in one fast call, which is much cheaper than probing
`get_measures` per station. Combinations without data are absent (spot-checked against
`measures`). The [bulk downloader](../downloader.md) uses it to skip empty combinations.

## Findings and limitations

- **One station per call**: `measures` without a `station` parameter fails with HTTP 500, so
  query one station at a time.
- **Hours 1–24**: the API counts hours 1–24. `canairy` converts `datetime`s to `(date, hour+1)`
  for requests and back (`time - 1h`, `24:00` → next day `00:00`) for responses, so you work with
  regular 0–23 hours. Results are naive datetimes.
- **Data start**: measurements start on 2016-01-01.
- **`meta` endpoint**: times out (HTTP 504), so it is not wrapped.
- **`measureslimits`**: `measures/limits` also works, but not with the `/json` suffix.
- **Column-oriented responses**: the API returns an `indices` list naming the columns, and rows
  as positional lists keyed by numeric strings or nested station → start date dicts.
  Components and scopes are zipped against the model field order, so the field order must match
  the API's; `EXPECTED_*_INDICES` constants guard this and raise `ValueError` on drift.
  Measures are zipped against the response indices, normalized to field names.
- **Station rows** arrive as flat dicts with prefixed keys (`"type …"`, `"network …"`,
  `"setting …"`) and are regrouped into nested models.
- **Retries**: besides dropped connections, HTTP 429 and 5xx are retried with backoff; other
  4xx raise `HTTPStatusError` immediately. Responses are cached for 3 hours (see
  [HTTP behaviour](../http.md)).
- **Schleswig-Holstein** has no API of its own; its open-data portal links to old UBA URLs.
  Use this client for SH.
