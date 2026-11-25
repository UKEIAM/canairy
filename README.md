<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/UKEIAM/canairy/develop/docs/assets/logo-dark.svg">
    <img src="https://raw.githubusercontent.com/UKEIAM/canairy/develop/docs/assets/logo-light.svg" alt="canairy" width="420">
  </picture>
</h1>

[![PyPI](https://img.shields.io/pypi/v/canairy)](https://pypi.org/project/canairy/)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14%20%7C%203.15-blue)](https://github.com/UKEIAM/canairy/actions/workflows/tests.yml)
[![Coverage](https://raw.githubusercontent.com/UKEIAM/canairy/coverage-badge/badge.svg)](https://github.com/UKEIAM/canairy/actions/workflows/tests.yml?query=branch%3Adevelop)
[![License](https://img.shields.io/pypi/l/canairy)](https://github.com/UKEIAM/canairy/blob/develop/LICENSE)

Typed Python clients for public German air-quality APIs.

Miners once carried canaries to warn them of bad air underground. `canairy` does
the modern equivalent: it fetches official air-quality measurements and hands
them to you as validated [pydantic](https://docs.pydantic.dev) models.

Supported data sources:

| Module         | Source                                                                                        | Coverage                         |
| -------------- | --------------------------------------------------------------------------------------------- | -------------------------------- |
| `canairy.uba`  | [Umweltbundesamt](https://luftdaten.umweltbundesamt.de) (UBA), air-data API v4                | All of Germany, from 2016        |
| `canairy.hh`   | [Hamburger Luftmessnetz](https://hamburg.luftmessnetz.de) (HH)                                | Hamburg, hourly/daily from 2012, monthly from 1984 |
| `canairy.be`   | [Berliner Luftgütemessnetz](https://luftdaten.berlin.de) (BLUME, BE)                         | Berlin, hourly/daily back to the station start (1980s/90s) |
| `canairy.ni`   | [Lufthygienisches Überwachungssystem Niedersachsen](https://www.luen-ni.de) (LÜN, NI)         | Niedersachsen, hourly, last 30 days only |
| `canairy.nrw`  | [LANUK Nordrhein-Westfalen](https://luftqualitaet.nrw.de) (NRW)                               | NRW, hourly from 2020, daily/monthly/yearly from 2010 |

More federal-state networks are planned.

## Features

- One client class per data source with typed `get_*` methods
- Responses parsed into pydantic models with real `datetime`s
- Built-in HTTP caching ([hishel](https://hishel.com)), rate limiting (120 requests/min per API host; cache hits don't count) and retries with exponential backoff
- `aq-downloader` command for bulk downloads of UBA data

## Installation

```sh
pip install canairy
# or
uv add canairy
```

Requires Python 3.12 or newer (tested on 3.12–3.15).

> **Note:** `canairy` is pre-1.0. Expect breaking changes between minor versions.

## Quickstart

### Umweltbundesamt (UBA)

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

Components and scopes are numeric ids. Look them up with the metadata endpoints:

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

Find stations and filter them:

```python
from canairy.uba.utils import filter_stations_active, filter_stations_by_network

stations = uba.get_stations(lang="en").data        # ~2,400 stations, incl. closed ones
networks = uba.get_networks(lang="en").data

hamburg = filter_stations_by_network(stations, networks, "HH")
running = filter_stations_active(hamburg, "2020-01-01", "2024-12-31")
```

Other endpoints: `get_networks()` and `get_thresholds(use, component_id, scope_id)`.

### Hamburger Luftmessnetz (HH)

```python
from datetime import datetime

from canairy.hh import HHClient

hh = HHClient()

# Hourly NO₂ at all Hamburg stations
data = hh.get_component_data(
    "no2_1h",
    timespan="custom",
    start=datetime(2024, 1, 1, 0),
    end=datetime(2024, 1, 1, 3),
)
for d in data[:2]:
    print(d.datetime, d.station, d.value)
# 2024-01-01 03:00:00+01:00 80kt 31.0
# 2024-01-01 03:00:00+01:00 21bi 11.0

# Data for a single station
hh.get_station_data(
    "13ST", period="1h", timespan="custom",
    start=datetime(2024, 1, 1), end=datetime(2024, 1, 1, 3), core="no2",
)
```

Component codes combine a pollutant ("core") and an averaging period, for
example `no2_1h`, `pm10_24hg` or `pm25_1m`. List them with `get_components()`
and `get_cores()`. The other endpoints are `get_stations()`, `get_station(code)`
and `get_thresholds()`.

`canairy.hh.aqi` contains the bins, thresholds and ratings of the German air
quality index (Luftqualitätsindex) as used by the Hamburg network.

### Berliner Luftgütemessnetz (BE)

Berlin runs the same software as Hamburg, so `BEClient` has the same methods,
parameters and behaviour as `HHClient`; its models carry a `BE` prefix
(`BEStation`, `BEComponentData`, …).

```python
from datetime import datetime

from canairy.be import BEClient

be = BEClient()

be.get_station_data(
    "mc010", period="1h", timespan="custom",
    start=datetime(2024, 1, 1), end=datetime(2024, 1, 1, 3), core="no2",
)
```

Station codes look like `mc010` (EU code `DEBE010`). Berlin also offers
12-month moving means (`*_12mg`, monthly, from 2019).

### Lufthygienisches Überwachungssystem Niedersachsen (NI)

LÜN has no queryable API. It publishes one documented JSON file with the hourly
values of all stations over the last 30 days, updated every hour.
`NIClient.get_data()` fetches and parses the whole file:

```python
from canairy.ni import NIClient

data = NIClient().get_data()
print(data.timestamp)                          # 2026-11-25 10:00:00+01:00
print([s.code for s in data.stations][:3])     # ['BGSW', 'BGVT', 'BLWW']
print([c.code for c in data.components][:3])   # ['PM1024', 'NO2', 'O3']

no2 = data.get_series("BGSW", "NO2")
for v in no2.values[-2:]:
    print(v.datetime, v.value, v.detection_limit)
# 2026-11-25 09:00:00+01:00 10.0 None
# 2026-11-25 10:00:00+01:00 None None
```

Each `NISeries` holds 720 hourly `NIValue`s, oldest first. `PM1024` is PM10 as a
moving 24-hour mean, `CO` an 8-hour mean; see `NIComponent.averaging`.

### Nordrhein-Westfalen (NRW)

NRW publishes a [documented API](https://luftqualitaet.nrw.de/apidoku.php). Stations,
components, methods, matrices, units and aggregations are numeric ids:

```python
from datetime import date, datetime

from canairy.nrw import NRWClient

nrw = NRWClient()

nrw.get_components()          # 1 O3, 2 SO2, 3 NO2, 200 PM10, 201 PM2.5, …
(station,) = nrw.get_stations(eu_code="DENW094", include_components=True)
station.id, station.name      # (1, 'Aachen-Burtscheid')

# Hourly NO₂ and PM10 at all stations; arguments taking ids also take lists
data = nrw.get_hourly([3, 200], datetime(2026, 11, 24, 0), datetime(2026, 11, 24, 3))
for m in data[:2]:
    print(m.station, m.component, m.start, m.value, m.below_detection_limit)
# 1 3 2026-11-24 00:00:00+01:00 21.597 False
# 1 200 2026-11-24 00:00:00+01:00 15.341 False

nrw.get_daily(200, date(2026, 11, 1), date(2026, 11, 3), station=1)
nrw.get_yearly(3, [2024, 2025], station=1)
```

Measurements: `get_hourly`, `get_moving_8h`, `get_daily`, `get_daily_sums`,
`get_daily_8h_max`, `get_4day`, `get_monthly`, `get_monthly_sums`, `get_yearly`,
`get_yearly_sums`. Further: `get_availability` (first/last day with data per
series), `get_pm10_exceedance_days`, `get_air_quality_index`,
`get_total_air_quality_index` and `get_ozone_warnings`.

### Working with DataFrames

All results are pydantic models, so they convert easily:

```python
import polars as pl  # or pandas

df = pl.DataFrame([m.model_dump() for m in res.data])
```

## Bulk download (`aq-downloader`)

```sh
aq-downloader <outpath> [-y YEAR_START]
```

Downloads hourly data for PM10, PM2.5, O₃, NO₂ and SO₂ and 8-hour CO for **every**
UBA station from `YEAR_START` (default 2016) up to last year. Each result is stored
as a pickled dict at `<outpath>/<year>/<station_code>/<component>_<scope>.pkl`,
and progress is logged to `<outpath>/download.log`. Expect this to run for a long
time.

A Docker image for the downloader lives in [`downloader/`](https://github.com/UKEIAM/canairy/tree/develop/downloader).

## Good to know

- **Caching:** responses are cached in `.cache/hishel/hishel_cache_v2.db` under the current working
  directory for as long as the servers allow: 5 minutes for HH and BE and 3 hours
  for UBA, measurements included. Repeated calls within that time don't hit the API.
  Other files in `.cache/hishel/`, left by canairy versions before the switch to hishel 2.0,
  are no longer read and can be deleted.
- **UBA**
  - `get_measures` needs a station; query one station at a time.
  - The API counts hours 1–24; `canairy` converts to regular 0–23 `datetime`s for you.
  - Data starts on 2016-01-01.
- **HH and BE** (same API)
  - The API silently shortens long ranges, keeping the *latest* 31 days for
    `1h`, `8hg` and `24hg` and the latest 365 days for `24h`. With
    `timespan="custom"`, `get_station_data` and `get_component_data` split
    longer ranges into several requests and join the results, so a year of hourly
    data costs about 12 requests. Other timespans are not split, and passing
    `start`/`end` with them raises `ValueError`; `get_component_data` treats
    `start`/`end` without a timespan as custom.
  - A missing `end` means now in Germany. A `start` after `end` raises
    `ValueError`; an open range that starts in the future returns `[]`.
  - Times are local (Europe/Berlin). Naive `start`/`end` are taken as German
    local time and aware ones are converted, so a timestamp from a previous result can
    be passed back as is. Results carry `+01:00`/`+02:00` offsets.
  - Rows come newest first.
  - `timespan="all"` on station data does not return everything: in Hamburg
    the last 12 months, in Berlin (`period="1h"`) the last month.
  - In Berlin, a few virtual and internal stations (e.g. `vir-v`) have no EU
    code, address, coordinates or URL; these fields are `None`.

- **NI**
  - Only the last 30 days are available, and the data are provisional
    (not fully validated). Collect the file regularly for longer series.
  - Timestamps mark the *end* of the averaging interval, in German local time.
  - Missing values (`***`) have `value=None`. Values below the detection
    limit (`<2`) have `value=None` and `detection_limit=2.0`.
  - `air_quality` is the current index of a pollutant (≤ 2 very good, > 6 very
    bad); it is `None` for meteorological components and when the current
    value is missing.
- **NRW**
  - Measurement methods return the intervals that lie completely within
    `[start, end]`, so `end` is effectively exclusive: daily means from
    1 to 3 November cover the 1st and 2nd. `start` must be before `end`.
  - The API works in CET (UTC+1) all year. Results carry `+01:00`, so a
    daily mean starts at midnight CET even in summer. Naive `start`/`end` are taken
    as German local time, aware ones are converted.
  - Values below the detection limit have `value=None` and
    `below_detection_limit=True`; `raw_value` keeps the measured number.
    Missing hours are absent rows. `validated` is `False` for provisional data.
  - Station coordinates are UTM zone 32N (`utm_east`/`utm_north`, EPSG:25832).
  - The API caps a response at 3 million rows. A response that does not
    parse as rows raises `ValueError`; split large queries by station or time.
  - Responses are not cached (`Cache-Control: max-age=0`).

## Development

```sh
uv sync                            # install with dev dependencies
uv run pytest                      # all tests, including live API calls
uv run ruff check src tests
uv run mypy src

# offline tests only
uv run pytest --ignore=tests/hh/test_hh_client.py --ignore=tests/be/test_be_client.py --ignore=tests/ni/test_ni_client.py --ignore=tests/nrw/test_nrw_client.py --ignore-glob='tests/uba/test_get_*.py'
```

## License

BSD 3-Clause, © 2025 Institut für Angewandte Medizininformatik. See [LICENSE](https://github.com/UKEIAM/canairy/blob/develop/LICENSE).

The data itself is provided by the Umweltbundesamt, the Hamburger
Luftmessnetz, the Berliner Luftgütemessnetz, the Lufthygienisches Überwachungssystem
Niedersachsen and the LANUK Nordrhein-Westfalen under their respective terms of use.
