# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python library (`canairy`, src layout) wrapping public air-quality APIs, plus a bulk-download CLI. Three API clients exist:

- `canairy.hh` — Hamburg, Hamburger Luftmessnetz (`https://hamburg.luftmessnetz.de/api`)
- `canairy.be` — Berlin, Berliner Luftgütemessnetz BLUME (`https://luftdaten.berlin.de/api`); same software and API as HH
- `canairy.ni` — Niedersachsen, LÜN (`https://www.luen-ni.de/json30m.txt`); a single documented JSON file, not a queryable API
- `canairy.nrw` — Nordrhein-Westfalen, LANUK (`https://luftqualitaet.nrw.de/api`), documented at `https://luftqualitaet.nrw.de/apidoku.php`
- `canairy.uba` — Umweltbundesamt air-data v4 (`https://luftdaten.umweltbundesamt.de/api/air-data/v4`)

The package is a pure API client: analysis code (data loading, exposure indices) lives outside this repository.

## Commands

Dependencies are managed with `uv` (`uv.lock` is committed; dev tools are in the `dev` dependency group). Supported Python: 3.12–3.15 (mypy checks against 3.12); test other versions with `uv run --python 3.15 --isolated pytest …`.

```sh
uv sync                                   # install incl. dev group
uv run pytest                             # all tests, incl. live API integration tests
uv run pytest --ignore=tests/hh/test_hh_client.py --ignore=tests/be/test_be_client.py --ignore=tests/ni/test_ni_client.py --ignore=tests/nrw/test_nrw_client.py --ignore-glob='tests/uba/test_get_*.py'  # offline only
uv run pytest tests/uba/test_get_measures.py::<name>  # single test
uv run coverage run -m pytest && uv run coverage report  # tests with coverage (config in pyproject.toml)
uv run ruff check src tests               # lint
uv run mypy src                           # type check (pydantic mypy plugin enabled)
uv run aq-downloader <outpath> -y 2016    # bulk UBA download CLI
```

Tests in `tests/hh/test_hh_client.py`, `tests/be/test_be_client.py`, `tests/ni/test_ni_client.py`, `tests/nrw/test_nrw_client.py` and `tests/uba/test_get_*.py` are integration tests against the real APIs (network required, subject to rate limits/caching). `tests/test_http.py`, `tests/uba/test_client.py`, `tests/uba/test_measures_limits.py`, `tests/scripts/`, `tests/ni/test_ni_models.py`, `tests/nrw/test_nrw_models.py` and `tests/luftmessnetz/test_*.py` are offline; `tests/uba/test_utils.py` is not run by the integration job but its station-filter tests do hit the live API.

## Architecture

The luftmessnetz clients (HH, BE) and the UBA client share the same shape, implemented independently (no API logic shared between luftmessnetz and UBA; only HTTP plumbing lives in `canairy._http`):

- A client class with typed public `get_*` methods. Each builds a pydantic `*Params` model, calls `_get`, and parses the JSON via a `from_response` classmethod on a response model.
- `_get` dumps params with `model_dump(exclude_none=True)`, sends one GET and calls `raise_for_status().json()`. Rate limiting and retries happen in the transport stack built by `canairy._http.build_client`: `Client → CacheTransport → RetryTransport → RateLimitTransport → HTTPTransport`. The limiter sits below the cache, so cache hits are free, and below the retry layer, so retries count.
- `RateLimitTransport`: at most `CALLS = 120` requests per `PERIOD = 60` s (sliding window) **per host, process-wide**, so HH, BE and UBA each have their own budget, and extra client instances don't raise it.
- `RetryTransport`: retries `httpx2.RemoteProtocolError` (also when raised while reading the body, so it buffers each body) and the client's `retry_statuses` with exponential `2**i` s backoff, `MAX_RETRIES = 8` attempts; once exhausted it re-raises the error or returns the last response. Timeouts and connect errors are not retried. Offline tests build clients with `build_transport(httpx2.MockTransport(...))` to keep the retry/limit layers.
- HTTP goes through `httpx2` (not `httpx`): `httpx2.Client(timeout=60)` with a `hishel.httpx2.CacheTransport(rfc=True)` on top of the stack, so repeated calls may be served from cache. Keep `rfc=True`: hishel 2.0's default ignores `Cache-Control` and caches every GET forever. Because an explicit transport is passed, env proxies (`HTTP(S)_PROXY`) bypass the stack.
- `_typing.py` holds `Literal` aliases for allowed API parameter values; `_models.py` holds pydantic params/response models.

Luftmessnetz (HH Hamburg, BE Berlin) specifics:
- Both networks run the same software; their Swagger specs (`/api/doc`) are identical apart from title. All code lives in the private `canairy._luftmessnetz` package (`LuftmessnetzClient`, neutral model names like `Station`). `canairy.hh`/`canairy.be` only subclass the client with a `BASE_URL` and re-export the models under `HH`/`BE`-prefixed aliases (`HHStation is BEStation`). Offline tests for the shared code are in `tests/luftmessnetz/`.
- Responses are lists of objects; models subclass `ItemListModel` and use `validation_alias` for camelCase fields.
- `_get` sends a single GET per call (all endpoints answer with a content-length; there is no HEAD probe or streaming path).
- No retry statuses: only dropped connections (`RemoteProtocolError`) are retried.
- Datetimes are serialized as `%d.%m.%Y %H:%M` and interpreted as Europe/Berlin local time; `DatetimeRangeParams` converts aware datetimes to naive Berlin time (naive ones are taken as Berlin time). Responses carry `+01:00`/`+02:00` offsets.
- **Silent truncation** (measured on HH and BE, identical): the API moves a custom `start` forward to `end - 31 days` for `1h`, `8hg`, `24hg` and `end - 365 days` for `24h` (local calendar days, both ends inclusive, so usually 745/366 timestamps), with HTTP 200 and no hint in the response. The spec at `/api/doc` only mentions "1 month" for `1h`/`24hg` and "1 year" for `24h`; `8hg` and the exact day counts were measured; they are fixed day counts, not calendar months (end `06.03.2025` moves start to `03.02.2025`, not `06.02.`). `RANGE_LIMITS` and `split_range` in `_client.py` encode this; `_get_data` requests custom ranges window by window (newest first) and drops the boundary row the windows share, keyed on `(datetime, station, component)`. For `get_component_data` the period comes from the code suffix (`pm10_1h` → `1h`, case-insensitive like the API); an unknown suffix only fails for custom ranges. Non-custom timespans (`lastyear`, `all`, …) are passed through unsplit and have not been probed for limits; neither have `1m`/`1y`/`*aot40`.
- Data rows come newest first, sorted by datetime across all stations/components (not grouped by component).
- HH: hourly/daily data start 2012-01-01; `*_1m` monthly means go back to 1984. `timespan="all"` on station data returns only the last 12 months.
- BE: hourly/daily data go back to the station start (e.g. 1995 for `mc174`); `timespan="all"` with `period=1h` returned only the last month. BE has an extra period `12mg` (12-month moving mean, monthly rows, from 2019-01, not truncated) and station group `suburb`. Some BE stations (virtual `vir-*`, internal `*-vgl`, `fub-ifm`, `mw088`) have null `codeEu`/`address`/`lat`/`lng`/`url`, hence the optional fields on `Station`.
- `aqi.py` contains static German AQI bins/thresholds/ratings, not API calls.

NI (Niedersachsen, LÜN) specifics:
- `NIClient.get_data()` fetches the whole ~1 MB file `json30m.txt` (documented in the appendix of `https://www.umwelt.niedersachsen.de/download/60236`; the file **alternates** between the documented format, `verlauf_stundenwerte` + hourly `verlauf_indexwerte`, and a newer one, `verlauf` + current `luftqualitaet` (its `Dateihistorie` then lists "verlauf_indexwerte entfernt", 2026-09-21); both were served on 2026-11-25 within an hour, and `_parse_series` reads both) and parses it into `NIData` (`canairy/ni/_models.py`). No other LÜN endpoints are used; the website's "Messwertarchiv" (90 days, CSV) is an undocumented frontend.
- The file is latin-1 without a charset header, so the client decodes `rsp.content` itself. Numbers are strings with a decimal comma. Values: `***` missing → `value=None`; `<x` below detection limit → `value=None`, `detection_limit=x`. `luftqualitaet` `0,00` means no current value → `air_quality=None`; in the documented format `NISeries.air_quality` is the newest `verlauf_indexwerte` value and each `NIValue` carries its hourly index.
- `verlauf` has 720 hourly values, oldest first; the last belongs to `datum`/`zeit`, local time with offset `zeitzone` (`UTC+1h`/`UTC+2h`), marking the end of the interval. Timestamps are stepped back in UTC and returned as Europe/Berlin aware datetimes.
- The server sends `ETag`/`Last-Modified` but no `Cache-Control`; hishel caches it heuristically for a few minutes.

NRW (Nordrhein-Westfalen, LANUK) specifics:
- One `get_*` method per documented endpoint (`{BASE_URL}/<name>.php`), all in `canairy/nrw/_client.py`; models and params in `_models.py`. Params models use the German API names and join id lists with commas (`Ids`).
- Measurement, AQI and ozone endpoints return positional arrays (default `index=array`; `index=obj` lowers the 3-million-row cap). Rows are zipped against the documented column tuples (`MEASUREMENT_COLUMNS`, `REFERENCE_MEASUREMENT_COLUMNS` for monthly/yearly/daily-8h-max, which add `mw_bezugszeit`, …); `RowModel.from_row` raises `ValueError` on a length mismatch. Column order is station, component, **matrix, method**, unit (the survey had matrix/method swapped).
- Values below the detection limit come as `"<10"` in `messwert` → `value=None`, `below_detection_limit=True`; `rohwert` → `raw_value`. Missing intervals are absent rows, not nulls.
- All times are CET (UTC+1) year-round, for requests and responses (checked with `zeitausgabe=unixtimestamp`; 29.03.2026 has a 02:00–03:00 row). Responses are parsed as aware `+01:00` datetimes and not converted, so day/month boundaries stay at midnight; request datetimes are converted with `to_cet` (naive = Europe/Berlin).
- A range returns intervals lying completely within `[beginn, ende]`; `ende` must be after `beginn` (422 otherwise; the client checks first). `beginn` requires `ende` on measurement endpoints; without a range they return everything since 2019-12-31, so the client requires one.
- Errors: HTTP 422 with `{"fehler": {"text": …}}` → `ValueError`; "Keine passenden Einträge gefunden" comes with HTTP 200 → `[]`.
- Hourly data start 2019-12-31 (meteorology 2020-01-01), daily/monthly/yearly 2010; even 2025 hourly data were still `freigabe=0` (provisional) in Nov 2026. `Cache-Control: max-age=0`, so nothing is cached. No retry statuses (only dropped connections). The 3-million-row hint format is unknown (untested).

UBA specifics:
- Each endpoint has its own subpackage (`components/`, `measures/`, `networks/`, `scopes/`, `stations/`, `thresholds/`); public models carry a `UBA` prefix (e.g. `UBAComponentsGetResponse`). `uba/_models.py` holds shared bases; `uba/utils.py` has station filters and index-normalization helpers. URLs are `{BASE_URL}/{endpoint}/json`.
- Retry statuses `UBA_RETRY_STATUSES` (429 and 5xx) besides `RemoteProtocolError`; other 4xx raise `HTTPStatusError` immediately.
- The API returns column-oriented data: an `indices` list naming columns and rows as positional lists (keyed by numeric strings or nested station → start-date dicts). Components and scopes zip rows against model field order, so **model field order must match the API column order**; `EXPECTED_*_INDICES` constants guard this and raise `ValueError` on drift. Measures zip rows against the response indices normalized to field names (`normalize_response_indices`).
- Time handling: the API uses hours 1–24. `from_dt` helpers convert `datetime` → `(date, hour+1)`; response parsing converts back (`time - 1h`, `24:00` → next day `00:00`).
- Station rows arrive as flat dicts with prefixed keys (`"type …"`, `"network …"`, `"setting …"`), regrouped by `Station.from_flat_dict`. Pass `lang="en"` for English type/setting names.
- `measures` without a `station` parameter fails (HTTP 500); query per station. Data starts 2016-01-01. The `meta` endpoint times out (504). `get_measures_limits` (`measureslimits/json`; `measures/limits` also works but not with the `/json` suffix) returns the first/last measurement start per scope × component × station in one fast call; combinations without data are absent (spot-checked against `measures`).

`canairy/scripts/downloader.py` (`aq-downloader` entry point) iterates years × all UBA stations (all of Germany) × `DEFAULT_COMPONENTS`, skips combinations whose `get_measures_limits` range misses the year (no file or station dir is written for them), and pickles `model_dump(mode="json")` results to `<outpath>/<year>/<station_code>/<component>_<scope>.pkl`, logging to `<outpath>/download.log`.


## Documentation

[Zensical](https://zensical.org) (`zensical.toml` at the root, pages in `docs/`, dependencies in the `docs` group). Build with `uv run --group docs zensical build --strict` (preview: `zensical serve`); strict mode aborts on broken links and anchors. CI runs the strict build in the lint job; `.github/workflows/docs.yml` builds and deploys the site to GitHub Pages (`https://ukeiam.github.io/canairy/`, `site_url` in `zensical.toml`) on pushes to `develop`. `docs/apis/index.md` ("Air quality APIs in Germany") is the survey of all state networks; `docs/apis/<client>.md` holds everything known about each implemented client (usage, findings, limitations). Update these pages together with the code when behaviour or findings change.

## CI

`.github/workflows/tests.yml` (push to `develop`, PRs, manual): ruff + mypy + strict docs build; offline tests on 3.12–3.15; live integration tests once on 3.15 (not per version, to respect API rate limits). Both test jobs run under `coverage` and upload their data files; the `coverage` job combines them, writes the report to the job summary and, on `develop` pushes, force-pushes the README badge (generated by `.github/scripts/coverage_badge.py`) to the orphan `coverage-badge` branch. The repo's Actions policy only allows GitHub-owned/verified actions plus a few orgs, so third-party actions like `py-cov-action` fail with `startup_failure`. All jobs use `uv sync --locked`, so keep `uv.lock` in sync with `pyproject.toml`.

## Docker

- `downloader/` (`build.zsh`, `run.zsh <host data dir>`): slim image `canairy_downloader` running `aq-downloader /data`.
