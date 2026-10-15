# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python library (`canairy`, src layout) wrapping public air-quality APIs, plus a bulk-download CLI. Two API clients exist:

- `canairy.hh` — Hamburg, Hamburger Luftmessnetz (`https://hamburg.luftmessnetz.de/api`)
- `canairy.uba` — Umweltbundesamt air-data v4 (`https://luftdaten.umweltbundesamt.de/api/air-data/v4`)

The package is a pure API client: analysis code (data loading, exposure indices) lives outside this repository.

## Commands

Dependencies are managed with `uv` (`uv.lock` is committed; dev tools are in the `dev` dependency group).

```sh
uv sync                                   # install incl. dev group
uv run pytest                             # all tests (most hit the live APIs)
uv run pytest tests/uba/test_utils.py                # offline unit tests only
uv run pytest tests/uba/test_get_measures.py::<name>  # single test
uv run ruff check src tests               # lint
uv run mypy src                           # type check (pydantic mypy plugin enabled)
uv run aq-downloader <outpath> -y 2016    # bulk UBA download CLI
```

Tests in `tests/hh/test_hh_client.py` and `tests/uba/test_get_*.py` are integration tests against the real APIs (network required, subject to rate limits/caching). `tests/uba/test_utils.py` and the other `tests/hh/test_*.py` files are offline.

## Architecture

Both clients share the same shape, implemented independently per package (no shared base module):

- A client class with typed public `get_*` methods. Each builds a pydantic `*Params` model, calls `_get`, and parses the JSON via a `from_response` classmethod on a response model.
- `_get` dumps params with `model_dump(exclude_none=True)`, is rate-limited with `ratelimit` (`@sleep_and_retry @limits(120, period=60)`), and wraps the request in a module-level `backoff()` (exponential `2**i` s, `MAX_RETRIES = 8`). Retry behaviour differs per client, see below; neither retries timeouts or connect errors.
- HTTP goes through a `hishel.httpx.SyncCacheClient` (timeout 60 s), so repeated calls may be served from cache.
- `_typing.py` holds `Literal` aliases for allowed API parameter values; `_models.py` holds pydantic params/response models.

HH (Hamburg) specifics:
- Responses are lists of objects; public models carry an `HH` prefix (e.g. `HHStation`), subclass `ItemListModel` and use `validation_alias` for camelCase fields.
- `_get` sends a single GET per call (all endpoints answer with a content-length; there is no HEAD probe or streaming path).
- `backoff()` retries only `httpx.RemoteProtocolError` and re-raises the last error once retries are exhausted.
- Datetimes are serialized as `%d.%m.%Y %H:%M` and interpreted as local time; responses carry `+01:00`/`+02:00` offsets.
- **Silent truncation:** the API moves a custom `start` forward to `end - 31 days` for `1h`, `8hg`, `24hg` and `end - 365 days` for `24h` (local calendar days, both ends inclusive, so usually 745/366 timestamps), with HTTP 200 and no hint in the response. The spec at `/api/doc` only mentions "1 month" for `1h`/`24hg` and "1 year" for `24h`; `8hg` and the exact day counts were measured. `RANGE_LIMITS` and `split_range` in `_client.py` encode this; `_get_data` requests custom ranges window by window (newest first) and drops the boundary row the windows share, keyed on `(datetime, station, component)`. For `get_component_data` the period comes from the code suffix (`pm10_1h` → `1h`). Non-custom timespans (`lastyear`, `all`, …) are passed through unsplit and have not been probed for limits; neither have `1m`/`1y`/`*aot40`.
- Data rows come newest first, sorted by datetime across all stations/components (not grouped by component).
- Hourly/daily data start 2012-01-01; `*_1m` monthly means go back to 1984. `timespan="all"` on station data returns only the last 12 months.
- `aqi.py` contains static German AQI bins/thresholds/ratings, not API calls.

UBA specifics:
- Each endpoint has its own subpackage (`components/`, `measures/`, `networks/`, `scopes/`, `stations/`, `thresholds/`); public models carry a `UBA` prefix (e.g. `UBAComponentsGetResponse`). `uba/_models.py` holds shared bases; `uba/utils.py` has station filters and index-normalization helpers. URLs are `{BASE_URL}/{endpoint}/json`.
- `backoff()` retries `httpx.RemoteProtocolError`, 5xx and 429, raises other 4xx immediately, and re-raises the last error once retries are exhausted.
- The API returns column-oriented data: an `indices` list naming columns and rows as positional lists (keyed by numeric strings or nested station → start-date dicts). Components and scopes zip rows against model field order, so **model field order must match the API column order**; `EXPECTED_*_INDICES` constants guard this and raise `ValueError` on drift. Measures zip rows against the response indices normalized to field names (`normalize_response_indices`).
- Time handling: the API uses hours 1–24. `from_dt` helpers convert `datetime` → `(date, hour+1)`; response parsing converts back (`time - 1h`, `24:00` → next day `00:00`).
- Station rows arrive as flat dicts with prefixed keys (`"type …"`, `"network …"`, `"setting …"`), regrouped by `Station.from_flat_dict`. Pass `lang="en"` for English type/setting names.
- `measures` without a `station` parameter fails (HTTP 500); query per station. Data starts 2016-01-01. The `meta` endpoint times out (504); `measures/limits` (not wrapped by the client) returns first/last date per scope × component × station in one fast call.

`scripts/downloader.py` (`aq-downloader` entry point) iterates years × all UBA stations (all of Germany) × `DEFAULT_COMPONENTS` and pickles `model_dump(mode="json")` results to `<outpath>/<year>/<station_code>/<component>_<scope>.pkl`, logging to `<outpath>/download.log`. Known bug: each year requests up to `datetime(year+1, 12, 31)`, so consecutive years overlap.


## Docker

- `downloader/` (`build.zsh`, `run.zsh <host data dir>`): slim image `canairy_downloader` running `aq-downloader /data`.
