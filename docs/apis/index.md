# Air quality APIs in Germany

Air quality in Germany is measured by the 16 federal states, each running its own network.
The Umweltbundesamt (UBA) collects the data of all state networks and publishes them through
one federal API. Several states also publish their data themselves, often earlier, at a
finer resolution or with extra components, but each in its own way.

This page surveys the machine-readable endpoints of every state network. The subpages
describe the networks `canairy` has a client for:

| Client | Network | Source | Coverage |
|---|---|---|---|
| [`canairy.uba`](uba.md) | Umweltbundesamt (federal) | REST JSON, API v4 | All of Germany, from 2016 |
| [`canairy.hh`](hh.md) | Hamburger Luftmessnetz | REST JSON (luftmessnetz software) | Hamburg, hourly/daily from 2012, monthly from 1984 |
| [`canairy.be`](be.md) | Berliner Luftgütemessnetz (BLUME) | REST JSON (luftmessnetz software) | Berlin, hourly/daily back to the station start |
| [`canairy.ni`](ni.md) | Lufthygienisches Überwachungssystem Niedersachsen (LÜN) | documented JSON file | Niedersachsen, hourly, last 30 days only |
| [`canairy.nrw`](nrw.md) | LANUK Nordrhein-Westfalen | documented REST JSON | NRW, hourly from 2020, daily/monthly/yearly from 2010 |

## Survey of the state networks

Each state's network was searched for machine-readable endpoints, time-boxed to about
5 minutes per state. Probed on **2026-11-24** with plain `curl`. "Live" means the smoke test
returned values for the current day (13:00/14:00 CET).

None of the endpoints below are versioned public APIs, except NI's documented feed and NRW's
documented REST API. Most are frontend backends that may change without notice.

### Summary

| State | Network | Endpoint type | Base URL | Smoke test |
|---|---|---|---|---|
| BW Baden-Württemberg | LUBW | JSON (LUPO frontend backend) | `https://lupo-cloud.de/air-app/` | ✅ live |
| BY Bayern | LfU / LÜB | static CSV per station × component | `https://www.lfu.bayern.de/_data_extern/luft/immissionsmessungen/csv/` | ✅ live |
| BE Berlin | BLUME | REST JSON, same software as HH ([implemented](be.md)) | `https://luftdaten.berlin.de/api` | ✅ live |
| BB Brandenburg | LfU BB | CSV export (Liferay portlet), current hour only | `https://luftdaten.brandenburg.de/luftguete?...exportCsv` | ✅ live |
| HB Bremen | BLUES | CSV export (luftmessnetz frontend, like HH; no `/api`) | `https://bremen.luftmessnetz.de/station/<code>.csv` | ✅ live |
| HH Hamburg | Hamburger Luftmessnetz | REST JSON ([implemented](hh.md)) | `https://hamburg.luftmessnetz.de/api` | ✅ live |
| HE Hessen | HLNUG | none found; download form behind Friendly Captcha | `https://www.hlnug.de/messwerte/datenportal/` | ❌ |
| MV Mecklenburg-Vorpommern | LUNG / LUME | CSV download API (hourly) + JSON POST (HTML/Chart.js inside, aggregations) | `https://umweltportal.mv-regierung.de/lung/lume/api/` | ✅ live |
| NI Niedersachsen | LÜN | **documented** JSON file, 30 days ([implemented](ni.md)) | `https://www.luen-ni.de/json30m.txt` | ✅ live |
| NW Nordrhein-Westfalen | LANUK | **documented** REST JSON ([implemented](nrw.md)) | `https://luftqualitaet.nrw.de/api/` | ✅ live |
| RP Rheinland-Pfalz | ZIMEN | JSON index + CSV files (last 8 h) | `https://zimen.webraum.rlp.de/zimen/data.php` | ✅ live |
| SL Saarland | IMMESA | HTML tables only (scraping) | `https://umweltserver.saarland.de/extern/luft/` | ⚠️ live, HTML only |
| SN Sachsen | LfULG | ASP.NET WebForms CSV postback (needs ViewState) | `https://www.umwelt.sachsen.de/umwelt/infosysteme/luftonline/` | ❌ not tested |
| ST Sachsen-Anhalt | LÜSA | JSON (LUPO frontend backend) | `https://lupo-cloud.de/st-air-app/` | ✅ live |
| SH Schleswig-Holstein | LÜSH | none of its own; open data links to UBA | (UBA API) | ❌ |
| TH Thüringen | TLUBN | JSON (LUPO frontend backend) | `https://lupo-cloud.de/th-air-app/` | ✅ live |

### Shared platforms

One client could cover several states:

- **luftmessnetz software** (HH, BE, HB): Hamburg and Berlin expose the same `/api`, and
  `canairy.hh` and `canairy.be` share one implementation. Bremen runs the same frontend but
  answers `/api/*` with 404, so only its CSV export is available. See
  [Hamburg](hh.md#the-luftmessnetz-software) for the vendor and the stack.
- **LUPO cloud** (BW, ST, TH): `https://lupo-cloud.de/<prefix>/{stations,station,table}` with
  prefixes `air-app` (BW), `st-air-app` (ST), `th-air-app` (TH). The response shapes differ slightly
  between BW and ST/TH.
- **Liferay** (BB, ST, TH portals): the portals themselves only embed data; the data sits elsewhere.

## Details per state

States with a client are described on their own pages: [Berlin](be.md), [Hamburg](hh.md),
[Niedersachsen](ni.md) and [Nordrhein-Westfalen](nrw.md).

### Baden-Württemberg (LUBW)

- Found in the page source of `https://www.lubw.baden-wuerttemberg.de/luft/messwerte-immissionswerte`
  (that host returns 403 to curl's default user agent; use a browser UA).
- `GET https://lupo-cloud.de/air-app/stations` → `{"selector":{"stations":[{"id":"DEBW029","name":"Aalen","lat":…,"lon":…},…]}}`
- `GET https://lupo-cloud.de/air-app/station?id=DEBW029&component=no2` → `infoPanel.station` with
  latest/min/max/avg for today and yesterday per component (NO2, O3, PM10, PM2.5, LUQX index). The
  `*Chart` keys came back empty in the test, and no hourly time series was found yet.
- `table?component=no2&id=…` returned `{"table":{}}`.
- Also: UDO (`https://udo.lubw.baden-wuerttemberg.de/public/`), an interactive export UI, linked per component.

### Bayern (LfU)

- Station pages: `https://www.lfu.bayern.de/luft/immissionsmessungen/messwerte/stationen/detail/<station>/<comp>`
- CSV: `https://www.lfu.bayern.de/_data_extern/luft/immissionsmessungen/csv/csv_<station>_<comp>.csv`
    - Example `csv_607_130.csv` (component 130 = PM2.5): rows `24.11.2026;13:00;8`, newest first, last 48 h,
      `;`-separated, no header.
    - Component codes seen: 130 (PM2.5), 172, 180. The station/component code list still has to be
      taken from the station index page `…/messwerte/stationen/index.htm`.
- No JSON API found.

### Brandenburg (LfU Brandenburg)

- Portal `https://luftdaten.brandenburg.de/` (Liferay), station pages `/w/<slug>`.
- CSV snapshot of the current hour for all stations:
  `https://luftdaten.brandenburg.de/luftguete?p_p_id=zitbb_luftguete_portlet_LuftguetePortlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=exportCsv&p_p_cacheability=cacheLevelPage`
    - latin-1, `;`-separated, quoted, HTML (`<sub>`) inside the column headers, decimal comma.
    - Station names only, no EU codes.
- No time-series endpoint found within the time box.

### Bremen (BLUES)

- `https://luftmessnetz.bremen.de/` redirects/links to `https://bremen.luftmessnetz.de/` (luftmessnetz frontend).
- `/api/*` → 404, so there is no JSON API, although it runs the same Faibl software as HH/BE
  (the API is apparently not enabled for Bremen).
- CSV per station with a custom range:
  `https://bremen.luftmessnetz.de/station/DEHB001.csv?group=pollution&period=1h&timespan=custom&start[date]=23.11.2026&start[hour]=14&end[date]=24.11.2026&end[hour]=14`
    - 4 header rows (station, component, unit, period), then `23.11.2026 14:00;12;21;…`.
- Stations: DEHB001, 002, 004, 005, 006, 012, 013, 014, 015 (from `/lqi`).

### Hessen (HLNUG): not found

- Data portal `https://www.hlnug.de/messwerte/datenportal/messstelle/<medium>/<theme>/<station>` (TYPO3
  extension `tx_messdaten`, charts loaded via RequireJS `stationView.min.js`).
- The download form (`tx_messdaten_station[action]=downloadMeasurementsTable`) is protected by Friendly
  Captcha.
- No XHR endpoint found in the HTML or the JS within the time box. **Next step:** open the station page in a browser
  and watch DevTools → Network for the chart data request.

### Mecklenburg-Vorpommern (LUNG)

- Linked from `https://www.lung.mv-regierung.de/fachinformationen/luft/luftgueteueberwachung/`.
- Frontend: `https://umweltportal.mv-regierung.de/lung/lume/stationswerte`,
  `…/timejump?days=3&station=32&komp=PM2_5`.
- CSV API: `GET https://umweltportal.mv-regierung.de/lung/lume/api/download-stationsdaten?st=32&komp=PM2_5&tst=2026-11-22&tsp=2026-11-24`
    - `Stationsname,StationsID,Komponente,Datum,Zeit,Wert` / `Güstrow,32,PM2_5,2026-11-22,ZEIT0100,2.004`
    - The hour is encoded as `ZEIT0100`…`ZEIT2400` (1–24 notation, as in UBA). Ranges are limited to 400 days.
    - The CSV endpoint ignores `unit` and always returns hourly values.
- JSON: `POST /lung/lume/api/stationkomponenten`, used by the page (tested 2026-11-24, ~0.5 s):
    - Body (`Content-Type: application/json`):
      `{"st":"32","komp":"PM2_5","unit":"0.0","tst":"22.11.2026","tsp":"24.11.2026"}`
        - Dates are `DD.MM.YYYY`.
        - `unit` = `<Auswertung>.<Zeitversatz>`. Auswertung: `0` hourly, `1` daily mean, `2` monthly mean,
          `3` daily max, `4` daily mean combined, `5` sliding 24h mean combined, `6` monthly max,
          `7` 8h mean, `8` monthly mean combined. Zeitversatz is the hour offset, max 23 for `5` and 7 for `7`, otherwise 0.
    - Response: `{"status","result","formKomponenten","formAuswertung","formTimeOffset","formDateStart","formDateStop","linkStationDetails"}`.
      **The data is not structured JSON.** `result` is an HTML fragment with a `<canvas data-symfony--ux-chartjs--chart-view-value="…">`
      attribute holding an HTML-escaped Chart.js config. Parse it with `html.unescape` + `json.loads`
      to get `data.labels` and `data.datasets[].data`.
    - Formats differ per aggregation:
        - Hourly: labels like `22.11.2026 0100`…`2400` (1–24 notation), values are floats or `null` (future hours).
        - Daily: labels like `17. Nov. 2026` (German month abbreviations), values are **strings** (`"5.589"`).
        - 8h mean: labels like `17. Nov. 2026 08:00`, string values.
    - Test result: Güstrow PM2.5 hourly, 72 labels, latest value `24.11.2026 1400` = 1.415, so live.
    - Errors are not signalled: an unknown station still returns `status: "OK"`, with a German
      "Keine Daten im gewählten Zeitraum vorhanden." warning inside `result`.
    - `formKomponenten` (HTML `<select>`) lists the station's components: `PM10, PM2_5, NO2, O3, NO, NOx, WIG, TMP`.
      This is the only way found so far to discover components per station.
- Recommendation: use the CSV endpoint for hourly data, and the POST endpoint only for server-side
  aggregations and component discovery. The POST endpoint is effectively a scraping target with a JSON wrapper.

### Rheinland-Pfalz (ZIMEN)

- A widget script `https://zimen.webraum.rlp.de/zimen/zimen.v.js` is embedded on
  `https://luft.rlp.de/zentrales-immissionsmessnetz-zimen/luftschadstoffe`.
- `GET https://zimen.webraum.rlp.de/zimen/data.php?type=messwert` (also `messwert_t`, `station`, `station_t`)
  → JSON `{ "<md5>": {"file": "K01_aktuelleLuftmesswertePM10.csv", "type": "messwert", "name": "PM10"}, … }`
- `GET …/data.php?data=<md5>` → CSV, a title line `Luftmesswerte - PM10 [µg/m³] vom 24.11.2026 14:00`, then
  `Standorte; 14:00; 13:00; …` covering the last 8 hours plus the max 1h value; one row per station (by name).
- Only the last 8 hours are available, so the data must be polled continuously.

### Saarland (IMMESA): HTML only

- `https://umweltserver.saarland.de/extern/luft/` (note: `https://www.umweltserver…` has a TLS cert
  mismatch; `www.saarland.de` returns 403 for non-browser UAs).
- Current values: `immeakt2.php?status=no2` (also `so2`, `o3`, `co`, BTXS); daily/weekly series in
  `immegra2.php?a=<station>&b=<comp>`; a map in `immemap2.php`.
- The test page showed `1-Stunden-Mittelwerte am 24.11.2026 … 14:00 13:00 …`, latin-1, not validated.
- No CSV/JSON found, so it can only be scraped.

### Sachsen (LfULG): no API found

- `https://www.umwelt.sachsen.de/umwelt/infosysteme/luftonline/` (ASP.NET WebForms), and
  `https://www.luft.sachsen.de/aktuelle-messwerte-15045.html`.
- `Recherche.aspx` has a CSV button (`ctl00_ctl00_Inhalt_Inhalt_BtnCsvDown`), which requires a full
  `__VIEWSTATE` postback. That is feasible with a session, but was not tested within the time box.
- Prior art: GitHub `CodeforLeipzig/luftqualitaet_sachsen`.

### Sachsen-Anhalt (LÜSA)

- Portal `https://umwelt.sachsen-anhalt.de/luft-messwerte` (Liferay, LUPO theme).
- `GET https://lupo-cloud.de/st-air-app/stations` → `{"selector":{"stations":[{"label":"Aschersleben","id":"DEST095",…}]}}`
- `GET https://lupo-cloud.de/st-air-app/station?id=DEST095&component=no2&from=2026-11-24`
  → `infopanel.station.components.<comp>` with `latest_time` (epoch ms), `latest_value`, `max_today`, … .
  **`from` is required**; without it the response is `{"_s":false}`.
- `GET …/table?component=no2&id=DEST095` → `table-urban`/`-rural`/`-industry` rows with values for all stations.
- Also `https://dev.lupo-cloud.de/st-air-app/o3limit`.

### Schleswig-Holstein (LÜSH): no own API

- `https://www.schleswig-holstein.de/DE/fachinhalte/L/luftqualitaet/aktuelleluftschadstoffdaten`
  links to `https://umweltportal.schleswig-holstein.de/messwertsuche` (server-side form, no API seen) and
  to `https://opendata.schleswig-holstein.de/dataset?tags=Luft`.
- The CKAN datasets (one per station × component × year) only contain links to the old UBA
  `api/air_data/v2` URLs, which now return 301. For SH, use [`canairy.uba`](uba.md).

### Thüringen (TLUBN)

- Portal `https://www.umweltportal.thueringen.de/luft-messwerte` (Liferay, LUPO cooperation).
- `GET https://lupo-cloud.de/th-air-app/stations` → stations `DETH011`, …
- `GET https://lupo-cloud.de/th-air-app/station?id=DETH011&component=no2&from=2026-11-24` → same shape as ST;
  `displayTime: "Dienstag, 24. November 2026 14:00"`.
- The page template references `https://lupo-cloud.de/th-air-app/csv-export/csv/<station>_<COMP>…`. Guessed
  names (`DETH011_NO2.csv`) returned 400; the exact filename suffix is still unknown.
- Also `https://www.umweltportal.thueringen.de/opendata-luft` (not examined).

## Next candidates

Berlin, Niedersachsen and Nordrhein-Westfalen are done. Of the rest:

1. **LUPO** (BW/ST/TH): one client parameterized by app prefix; first find the time-series/CSV
   endpoint (browser DevTools). The current endpoints only give today's and yesterday's summaries.
2. **MV**, **BY**, **HB**, **RP**, **BB**: CSV-based clients; RP and BB only give recent snapshots,
   so they need polling.
3. **HE**, **SN**, **SL**, **SH**: fall back to the UBA API, or invest in DevTools inspection/scraping.
