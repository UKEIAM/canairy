# canairy
Python client for public air-quality APIs: Umweltbundesamt (UBA) and Hamburger Luftmessnetz.

## Example 1
Use data from the Umwelt Bundesamt (UBA)

```python
from datetime import datetime

from canairy.uba import UBAClient
import polars as pl


client = UBAClient()

# plot hourly NO2 values measured at station 'DENW124' between January and February 2019 
rsp = client.get_measures(
    datetime(2019, 1, 1, 0, 0),
    datetime(2019, 2, 1, 0, 0),
    "DENW134",
    5,
    2
)
df = pl.DataFrame(rsp.data)
df.plot.line(x='date_start', y='value').properties(width=600)
```

## Example 2
Use data from the Hamburger Luftmessnetz

```python
Display monthly PM10 data.

import canairy.hh as hh
import polars as pl


client = hh.HHClient()

res = client.get_component_data("pm10_1m")
res = pl.DataFrame(res)

res.plot.line(x='datetime', y='value', color='station').properties(width=800, height=400)
```
