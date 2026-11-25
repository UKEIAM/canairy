# Niedersachsen (NI)

| | |
|---|---|
| Module | `canairy.ni` (`NIClient`) |
| Network | [Lufthygienisches Überwachungssystem Niedersachsen](https://www.luen-ni.de) (LÜN) |
| Source | one documented JSON file, `https://www.luen-ni.de/json30m.txt` (~1.1 MB), updated hourly |
| Documentation | appendix "Beschreibung der json-Schnittstelle" of [Erläuterungen und Hinweise zu den LÜN-Daten](https://www.umwelt.niedersachsen.de/download/60236) (PDF) |
| Coverage | 28 stations, hourly values of the **last 30 days only**, provisional |

LÜN has no queryable API. It publishes one file with the hourly values of all stations over
the last 30 days. `NIClient.get_data()` fetches and parses the whole file.

## Usage

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

| Model | Content |
|---|---|
| `NIData` | `network`, `timestamp` (newest value), `comments`, `history`, `components`, `stations`, `series`; `get_series(station, component)` |
| `NIStation` | `code` (`BGSW`), `code_eu` (`DENI011`), `name`, `location`, `street`, `lat`, `lng`, `altitude`, `area`, `type`, `representativeness` |
| `NIComponent` | `code`, `name`, `unit`, `averaging` (e.g. "Einstundenmittelwert") |
| `NISeries` | `station`, `component`, `air_quality`, `values` (720 × `NIValue`, oldest first) |
| `NIValue` | `datetime`, `value`, `detection_limit`, `air_quality` (hourly index, only in the documented format) |

### Components

| Code | Component | Unit | Averaging |
|---|---|---|---|
| `PM1024` | PM10 | µg/m³ | moving 24-hour mean, updated hourly |
| `NO2`, `O3`, `SO2` | nitrogen dioxide, ozone, sulphur dioxide | µg/m³ | 1-hour mean |
| `CO` | carbon monoxide | mg/m³ | 8-hour mean |
| `CO2` | carbon dioxide | ppm | 1-hour mean |
| `TT`, `PPP`, `DD`, `FF`, `TF` | temperature, pressure, wind direction, wind speed, relative humidity | °C, hPa, Grad, m/s, % | 1-hour mean |
| `RD` | rain duration | min | 1-hour sum |
| `G`, `UVBSI` | global radiation, UV index | W/m², – | 1-hour mean |

Not every station measures every component (e.g. 20 of 28 stations measure ozone).

## Findings and limitations

- **30 days only.** Collect the file regularly to build longer series. The website's
  "Messwertarchiv" offers 90 days as CSV, but it is an undocumented frontend and not used.
- **Provisional data.** The file says so itself: the values have not passed all validation steps.
- **Encoding:** the file is latin-1 but served as `text/plain` without a charset; the client
  decodes it explicitly. Numbers are strings with a decimal comma.
- **Values:**
    - `***` (missing) → `value=None`.
    - `<2` (below the detection limit 2) → `value=None`, `detection_limit=2.0`.
- **Air quality index** of a pollutant: ≤ 2 very good, ≤ 3 good, ≤ 4 satisfactory, ≤ 5
  sufficient, ≤ 6 bad, > 6 very bad. `NISeries.air_quality` is the current index: `luftqualitaet`
  in the newer format, the newest hourly index in the documented one. `0,00` or `***` mark a
  missing current value → `None`; meteorological components have none.
- **Time stamps:** each `verlauf` has 720 hourly values, oldest first; the last belongs to the
  file's `datum`/`zeit`, local time with the offset given in `zeitzone` (`UTC+1h` or `UTC+2h`).
  Timestamps mark the **end** of the averaging interval. The client steps back in UTC, so the
  hours stay evenly spaced across DST changes, and returns Europe/Berlin aware datetimes.
- **Two file formats, alternating.** On 2026-11-25 the file switched between them within an
  hour, so both must be expected at any time; the client reads both:

    | | Documented format | Newer format |
    |---|---|---|
    | Hourly values | `verlauf_stundenwerte` | `verlauf` |
    | Air quality index | `verlauf_indexwerte` (720 hourly values) | `luftqualitaet` (current value only) |
    | `Dateihistorie` | ends with the 2024-01-08 entry | adds "21.09.2026-SK: verlauf_indexwerte entfernt" |

    The PDF describes the documented format. `PM1024` replaced `PM10` on 2022-09-16 in both.
- **Caching:** the server sends `ETag`/`Last-Modified` but no `Cache-Control`; the cache keeps
  the file for a few minutes (heuristic freshness).
