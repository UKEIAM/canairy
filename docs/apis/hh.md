# Hamburg (HH)

| | |
|---|---|
| Module | `canairy.hh` (`HHClient`) |
| Network | [Hamburger Luftmessnetz](https://hamburg.luftmessnetz.de) |
| API | `https://hamburg.luftmessnetz.de/api`, Swagger UI at [`/api/doc`](https://hamburg.luftmessnetz.de/api/doc) |
| Coverage | hourly and daily data from 2012-01-01, monthly means (`*_1m`) from 1984 |
| Shares its implementation with | [Berlin](be.md) |

## Usage

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

| Method | Endpoint | Returns |
|---|---|---|
| `get_stations(active=, include_hidden=)` | `stations` | `list[HHStation]` |
| `get_station(code)` | `stations/{code}` | `HHStation` |
| `get_components(active=, group_code=)` | `components` | `list[HHComponent]` |
| `get_cores()` | `cores` | `list[HHCore]` |
| `get_thresholds()` | `exceeds` | `list[HHThreshold]` |
| `get_component_data(code, stationgroup=, timespan=, start=, end=)` | `components/{code}/data` | `list[HHComponentData]` |
| `get_station_data(code, period=, timespan=, start=, end=, core=)` | `stations/{code}/data` | `list[HHStationData]` |

### Components, cores and periods

A component code combines a pollutant ("core") and an averaging period, for example
`no2_1h`, `pm10_24hg` or `pm25_1m`. List them with `get_components()` and `get_cores()`.

| Period | Meaning |
|---|---|
| `1h` | hourly mean |
| `24h` | daily mean |
| `8hg` | moving 8-hour mean |
| `24hg` | moving 24-hour mean |
| `1m` | monthly mean |
| `1y` | yearly mean |
| `1yaot40`, `5yaot40` | AOT40 ozone exposure (1 and 5 years) |
| `12mg` | 12-month moving mean (Berlin only) |

Timespans: `currentday`, `currentmonth`, `currentyear`, `lastday`, `lastweek`, `lastmonth`,
`lastyear`, `all` and `custom` (with `start`/`end`).

### Air quality index

`canairy.hh.aqi` holds the bins, thresholds and ratings of the German air quality index
(Luftqualitätsindex) as used by the Hamburg network. It is static data, not an API call:

- `components`: `no2_1h`, `so2_1h`, `o3_1h`, `co_8hg`, `pm10_24hg`
- `ratings`: 1 "sehr gut" … 6 "sehr schlecht"
- `clf_bins`: class limits per component, e.g. `no2_1h`: 25, 50, 100, 200, 500 µg/m³
- `clf_thresholds`: the limit value per component, e.g. `no2_1h`: 200 µg/m³

## Findings and limitations

### Silent truncation of long ranges

The API silently moves a custom `start` forward to `end - 31 days` for `1h`, `8hg` and `24hg`,
and to `end - 365 days` for `24h`. It answers with HTTP 200 and gives no hint in the response.
Both ends are inclusive and counted in local calendar days, so a truncated response usually
holds 745 (hourly) or 366 (daily) timestamps.

- The Swagger spec only mentions "1 month" for `1h`/`24hg` and "1 year" for `24h`. The `8hg`
  limit and the exact day counts were measured (identical on HH and BE).
- The limits are fixed day counts, not calendar months: end `06.03.2025` moves the start to
  `03.02.2025`, not `06.02.2025`.
- With `timespan="custom"`, `get_station_data` and `get_component_data` split longer ranges
  into windows the API returns whole, request them newest first and drop the boundary row
  the windows share (keyed on datetime, station and component). A year of hourly data costs
  about 12 requests.
- For `get_component_data`, the period comes from the code suffix (`pm10_1h` → `1h`, case
  insensitive like the API). An unknown suffix only fails for custom ranges.
- Non-custom timespans (`lastyear`, `all`, …) are passed through unsplit; their limits have not
  been probed, nor those of `1m`, `1y` and `*aot40` ([issue #21](https://github.com/UKEIAM/canairy/issues/21)).
- Passing `start`/`end` with a non-custom timespan raises `ValueError`. `get_component_data`
  treats `start`/`end` without a timespan as custom.

### Ranges and time zones

- Request datetimes are sent as `%d.%m.%Y %H:%M` and read by the API as German local time
  (Europe/Berlin). Naive `start`/`end` are taken as German local time and aware ones are
  converted, so a timestamp from a previous result can be passed back as is.
- Results carry `+01:00`/`+02:00` offsets.
- A missing `end` means now in Germany. A `start` after `end` raises `ValueError`; an open
  range that starts in the future returns `[]`.

### Responses

- Rows come newest first, sorted by datetime across all stations and components (not grouped
  by component).
- `timespan="all"` on station data returns only the last 12 months.
- Each call sends a single GET; all endpoints answer with a content length.
- Only dropped connections are retried; the API has no retry statuses. Responses are cached
  for 5 minutes (see [HTTP behaviour](../http.md)).

## The luftmessnetz software

Hamburg and Berlin run the same software and expose identical endpoints; their Swagger specs
(`/api/doc`) differ only in title and description and both report version `1.0.0`. In
`canairy`, all code lives in the private package `canairy._luftmessnetz`; `canairy.hh` and
`canairy.be` only set the base URL and re-export the models under prefixed names
(`HHStation is BEStation`).

- Vendor: **Faibl GmbH** (Hamburg), product "Luftmessnetz Online" (`https://luftmessnetz.de/`,
  checked 2026-11-25). The product page lists Berlin, Hamburg and Bremen as references; the
  Berlin [Impressum](https://www.berlin.de/luftdaten/impressum/) names Faibl as technical
  operator of `luftdaten.berlin.de`.
- Stack: PHP/Symfony (the Swagger page is generated by NelmioApiDocBundle), Apache behind Varnish.
- One multi-tenant codebase: frontend assets live under
  `/build/app/styles/clients/<city>/lmn-frontend.css`, and the asset cache-busters of HH and BE
  differ by 2 s (both deployed 2026-11-18 13:11 UTC).
- Hamburg's Content-Security-Policy still allows `*.berlin.de`, which suggests the code was
  first built for Berlin (inference, not documented).
- Bremen runs the same frontend, but answers `/api/*` with 404 (see the
  [survey](index.md#bremen-blues)).
- Other networks that buy the product with the API enabled could likely be added like
  `canairy.be`: a subclass with a new `BASE_URL`.
