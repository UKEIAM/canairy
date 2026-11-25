# Nordrhein-Westfalen (NRW)

| | |
|---|---|
| Module | `canairy.nrw` (`NRWClient`) |
| Network | [LANUK Nordrhein-Westfalen](https://luftqualitaet.nrw.de) (Landesamt für Natur, Umwelt und Klima) |
| API | `https://luftqualitaet.nrw.de/api/<endpoint>.php` |
| Documentation | [Dokumentation API LuftQualität.NRW](https://luftqualitaet.nrw.de/apidoku.php) |
| Coverage | 463 stations incl. closed and special-purpose sites; hourly from 2019-12-31 (meteorology 2020-01-01), daily/monthly/yearly from 2010 |
| Bulk open data | `https://www.opengeodata.nrw.de/produkte/umwelt_klima/luftqualitaet/luqs/` (not used) |

!!! note "Not yet on `develop`"
    `canairy.nrw` lives on the branch `feat/nrw-client` until it is merged.

## Usage

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

Stations, components, methods, matrices, units and aggregations are numeric ids. All
arguments taking ids also take a sequence of ids.

### Metadata

| Method | Endpoint | Returns |
|---|---|---|
| `get_components()` | `basis.php?tabelle=komponente` | `list[NRWComponent]` (97 components) |
| `get_methods()` | `basis.php?tabelle=methode` | `list[NRWMethod]` (online, filter, sorbent, passive sampler, …) |
| `get_matrices()` | `basis.php?tabelle=matrix` | `list[NRWMatrix]` (outdoor air, PM10, PM2.5, deposition) |
| `get_units()` | `basis.php?tabelle=einheit` | `list[NRWUnit]` |
| `get_aggregations()` | `basis.php?tabelle=aggregation` | `list[NRWAggregation]` |
| `get_station_classes()` | `basis.php?tabelle=stationsklasse` | `list[str]` |
| `get_station_environments()` | `basis.php?tabelle=stationsumgebung` | `list[str]` |
| `get_stations(station=, code=, eu_code=, component=, aggregation=, station_class=, environment=, include_components=)` | `station.php` | `list[NRWStation]` |
| `get_availability(station=, component=, aggregation=, method=, matrix=, start=, end=)` | `limits.php` | `list[NRWAvailability]` |

`include_components=True` adds each station's series (component, matrix, method, unit,
aggregation) with the first and last day with data. `get_availability` returns the same
ranges, filtered; without `start`, the API only looks at the last 5 months.

### Measurements

All return `list[NRWMeasurement]` and take `station=`, `method=` and `matrix=` filters.

| Method | Endpoint | Aggregation | Range |
|---|---|---|---|
| `get_hourly(component, start, end)` | `stundenmittelwerte.php` | 1, hourly mean | `datetime` |
| `get_moving_8h(component, start, end)` | `g8stundenmittelwerte.php` | 2, moving 8-hour mean (ozone only) | `datetime` |
| `get_daily(component, start, end)` | `tagesmittelwerte.php` | 4, daily mean | `date` |
| `get_daily_sums(component, start, end)` | `tagessummenwerte.php` | 7, daily sum | `date` |
| `get_daily_8h_max(component, start, end)` | `8stundenmaxima.php` | 16, daily max 8-hour mean (ozone only) | `date` |
| `get_4day(component, start, end)` | `4tagesmittelwerte.php` | 27, 4-day mean of samplers (e.g. benzene) | `date` |
| `get_monthly(component, start, end)` | `monatsmittelwerte.php` | 5, monthly mean | `date` |
| `get_monthly_sums(component, start, end)` | `monatssummenwerte.php` | 8, monthly sum | `date` |
| `get_yearly(component, years)` | `jahresmittelwerte.php` | 6, yearly mean | years |
| `get_yearly_sums(component, years)` | `jahressummenwerte.php` | 9, yearly sum | years |

`NRWMeasurement` fields: `station`, `component`, `matrix`, `method`, `unit`, `start`, `end`,
`reference` (`"2026-01"`, `"2025"` or `"2026-11-20"` for monthly, yearly and daily 8-hour
maxima), `value`, `raw_value`, `detection_limit`, `below_detection_limit`, `validated`.

### Indices and warnings

| Method | Endpoint | Returns |
|---|---|---|
| `get_pm10_exceedance_days(years, station=, method=)` | `pm10uetage.php` | `list[NRWExceedanceDays]`: days with a PM10 daily mean above 50 µg/m³ |
| `get_air_quality_index(component, start, end, station=)` | `lqindex.php` | `list[NRWAirQualityIndex]`: hourly index (1–6) of PM10 (200), PM2.5 (201), NO2 (3), SO2 (2) or O3 (1) |
| `get_total_air_quality_index(start=, end=, station=)` | `gesamtlqindex.php` | `list[NRWTotalAirQualityIndex]`: worst single index; without a range, the last available hour |
| `get_ozone_warnings(day=)` | `ozonwarnung.php` | `list[NRWOzoneWarning]`: level 0–5; by default today and the next two days |

- For stations without ozone, the total index uses a substitute ozone value (mean over all
  ozone stations except Simmerath, Essen-Schuir, Netphen and Lüdenscheid);
  `ozone_substitute` tells whether it determined the index.
- Ozone warnings use CAMS forecasts and, for today and past days, measurements. They are
  always provisional and may change during the day.
- For the current year, PM10 exceedance days are counted up to the end of the last evaluated
  month (aggregation 19 instead of 18).

## Findings and limitations

- **Ranges:** measurement methods return the intervals that lie **completely within**
  `[start, end]`, so `end` is effectively exclusive: daily means from 1 to 3 November cover the
  1st and 2nd; hourly means from 00:00 to 03:00 are three rows. `end` must be after `start`;
  the client checks this before sending (the API answers 422). Without any range, the
  measurement endpoints return everything since 2019-12-31, so the client requires one.
- **Time zone:** the API reads and writes all times in CET (UTC+1) **all year**; 29 March 2026
  has a 02:00–03:00 row, and `zeitausgabe=unixtimestamp` confirms the offset. Results carry
  `+01:00` and are not converted, so a daily mean starts at midnight CET even in summer. Naive
  `start`/`end` are taken as German local time and aware ones are converted.
- **Detection limit:** values below it come as strings like `"<10"` in `messwert`. They
  become `value=None` and `below_detection_limit=True`; `raw_value` keeps the measured number
  (`rohwert`), and `detection_limit` is the limit (`nwg`, `None` for sums and 8-hour maxima).
- **Missing values** are absent rows, not nulls.
- **Validation:** `validated` (`freigabe`) is `False` for provisional data. Even 2025 hourly
  data were still provisional in November 2026; yearly means of 2024/2025 were validated.
- **Row format:** measurement, index and warning endpoints return positional arrays
  (`index=array`). The client zips them against the documented column order and raises
  `ValueError` on a length mismatch. The order is station, component, **matrix, method**,
  unit, … (an earlier survey had matrix and method swapped). `index=obj` would give named
  fields, but lowers the row cap considerably.
- **Row cap:** a response holds at most 3 million rows; after that the API appends a hint,
  whose format is unknown (not tested). The client then raises `ValueError`; split large
  queries by station or time. For scale: hourly NO₂ of all 56 stations for one month is
  ~40,000 rows, 3 MB and 2 s.
- **Errors:** invalid parameters answer HTTP 422 with `{"fehler": {"text": …}}`, raised as
  `ValueError` with the German text. "Keine passenden Einträge gefunden" (no data) comes with
  HTTP 200 and becomes `[]`.
- **Row order:** by station, then time; components of one station are interleaved.
- **Stations:** many special-purpose sites have no EU code (164 of 463) or altitude (148).
  Coordinates are UTM zone 32N (`utm_east`/`utm_north`, ETRS89, EPSG:25832) and are passed
  through unconverted.
- **Daily hourly maxima:** aggregation 10 ("Stunden-Maximum Tag") is listed in the metadata
  and in station series, but the API has no endpoint for it.
- **Caching:** the API sends `Cache-Control: max-age=0`, so nothing is cached. Only dropped
  connections are retried. `gesamtlqindex` with a range can take several seconds.
