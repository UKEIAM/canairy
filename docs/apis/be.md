# Berlin (BE)

| | |
|---|---|
| Module | `canairy.be` (`BEClient`) |
| Network | [Berliner Luftgütemessnetz](https://luftdaten.berlin.de) (BLUME) |
| API | `https://luftdaten.berlin.de/api`, Swagger UI at [`/api/doc`](https://luftdaten.berlin.de/api/doc) |
| Coverage | hourly and daily data back to the station start (1980s/90s, e.g. 1995 for `mc174`) |
| Shares its implementation with | [Hamburg](hh.md) |

BLUME (**B**erliner **Lu**ftgüte-**Me**ssnetz) has been run since 1975 by the Senate
environment department (currently SenMVKU). Faibl GmbH operates `luftdaten.berlin.de`
technically.

Berlin runs the same software as Hamburg, so `BEClient` has the same methods, parameters and
behaviour as `HHClient`; its models carry a `BE` prefix (`BEStation`, `BEComponentData`, …).
Read the [Hamburg page](hh.md) for the methods, periods and timespans, the silent range
truncation, time zones and response order. This page lists what differs.

## Usage

```python
from datetime import datetime

from canairy.be import BEClient

be = BEClient()

be.get_station_data(
    "mc010", period="1h", timespan="custom",
    start=datetime(2024, 1, 1), end=datetime(2024, 1, 1, 3), core="no2",
)

# 12-month moving mean, monthly rows from 2019
be.get_component_data(
    "no2_12mg", timespan="custom",
    start=datetime(2024, 1, 1), end=datetime(2024, 12, 1),
)
```

Station codes look like `mc010` (EU code `DEBE010`).

## Differences from Hamburg

- **Extra period `12mg`**: 12-month moving mean, one row per month, from 2019-01. It is not
  truncated.
- **Extra station group `suburb`.**
- **Longer history**: hourly and daily data go back to the station start, not to 2012.
- **Stations without metadata**: a few virtual (`vir-*`), internal (`*-vgl`) and special
  stations (`fub-ifm`, `mw088`) have no EU code, address, coordinates or URL; these fields
  are `None`. Use `get_stations(include_hidden=True)` to see them.
- **`timespan="all"`** with `period="1h"` returned only the last month (Hamburg: 12 months).

## Findings

- Silent range truncation is the same as in Hamburg (checked 2026-11-24): 745 timestamps for
  `1h`/`8hg`/`24hg`, 366 for `24h`; `1m`, `1y` and `12mg` are not truncated. `canairy` splits
  long custom ranges for you.
- `timespan=last24h` is not a valid timespan: `stations/mc010/data?timespan=last24h&period=1h`
  answers `[]` instead of an error; `timespan=lastday` returns data.
- Example row of `components/no2_1h/data`:
  `{"datetime":"2026-11-24T13:00:00+01:00","station":"mc117","core":"no2","component":"no2_1h","period":"1h","value":12.0}`
