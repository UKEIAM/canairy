# canairy

Typed Python clients for public German air-quality APIs.

Miners once carried canaries to warn them of bad air underground. `canairy` does the modern
equivalent: it fetches official air-quality measurements and hands them to you as validated
[pydantic](https://docs.pydantic.dev) models.

## Data sources

| Module | Source | Coverage |
|---|---|---|
| [`canairy.uba`](apis/uba.md) | Umweltbundesamt (UBA), air-data API v4 | All of Germany, from 2016 |
| [`canairy.hh`](apis/hh.md) | Hamburger Luftmessnetz | Hamburg, hourly/daily from 2012, monthly from 1984 |
| [`canairy.be`](apis/be.md) | Berliner Luftgütemessnetz (BLUME) | Berlin, hourly/daily back to the station start |
| [`canairy.ni`](apis/ni.md) | Lufthygienisches Überwachungssystem Niedersachsen (LÜN) | Niedersachsen, hourly, last 30 days only |
| [`canairy.nrw`](apis/nrw.md) | LANUK Nordrhein-Westfalen | NRW, hourly from 2020, daily/monthly/yearly from 2010 |

[Air quality APIs in Germany](apis/index.md) surveys what the other federal states offer.

## Features

- One client class per data source with typed `get_*` methods
- Responses parsed into pydantic models with real `datetime`s
- Built-in HTTP caching, rate limiting and retries with exponential backoff
  (see [HTTP behaviour](http.md))
- `aq-downloader` command for [bulk downloads](downloader.md) of UBA data

## Installation

```sh
pip install canairy
# or
uv add canairy
```

Requires Python 3.12 or newer (tested on 3.12–3.15).

!!! warning "Pre-1.0"
    `canairy` is pre-1.0. Expect breaking changes between minor versions.

## Quickstart

```python
from datetime import datetime

from canairy.hh import HHClient

hh = HHClient()
data = hh.get_component_data(
    "no2_1h",
    timespan="custom",
    start=datetime(2024, 1, 1, 0),
    end=datetime(2024, 1, 1, 3),
)
```

Each data source has its own page with usage, findings and limitations.

## Working with DataFrames

All results are pydantic models, so they convert easily:

```python
import polars as pl  # or pandas

df = pl.DataFrame([m.model_dump() for m in data])
```

## License

BSD 3-Clause, © 2025 Institut für Angewandte Medizininformatik. The data itself is provided
by the Umweltbundesamt and the state networks under their respective terms of use.
