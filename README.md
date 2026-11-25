<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/UKEIAM/canairy/develop/docs/assets/logo-dark.svg">
    <img src="https://raw.githubusercontent.com/UKEIAM/canairy/develop/docs/assets/logo-light.svg" alt="canairy" width="420">
  </picture>
</h1>

[![PyPI](https://img.shields.io/pypi/v/canairy)](https://pypi.org/project/canairy/)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14%20%7C%203.15-blue)](https://github.com/UKEIAM/canairy/actions/workflows/tests.yml)
[![Coverage](https://raw.githubusercontent.com/UKEIAM/canairy/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/UKEIAM/canairy/blob/python-coverage-comment-action-data/htmlcov/index.html)
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

More federal-state networks are planned.

## Features

- One client class per data source with typed `get_*` methods
- Responses parsed into pydantic models with real `datetime`s
- Built-in HTTP caching ([hishel](https://hishel.com)), rate limiting (120 requests/min) and retries with exponential backoff
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

## Development

```sh
uv sync                            # install with dev dependencies
uv run pytest                      # all tests, including live API calls
uv run ruff check src tests
uv run mypy src

# offline tests only
uv run pytest --ignore=tests/hh/test_hh_client.py --ignore=tests/be/test_be_client.py --ignore-glob='tests/uba/test_get_*.py'
```

## License

BSD 3-Clause, © 2025 Institut für Angewandte Medizininformatik. See [LICENSE](https://github.com/UKEIAM/canairy/blob/develop/LICENSE).

The data itself is provided by the Umweltbundesamt, the Hamburger
Luftmessnetz and the Berliner Luftgütemessnetz under their respective terms of use.
