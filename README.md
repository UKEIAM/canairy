# de.uke.iam.air-pollution
Collect environmental data from multiple APIs

```python
Display monthly PM10 data.

import air_pollution.luftmessnetz as lmn
import polars as pl

client = lmn.LuftmessnetzClient()

res = client.get_component_data("pm10_1m")
res = pl.DataFrame(res)

res.plot.line(x='datetime', y='value', color='station').properties(width=800, height=400)
```

## Note
Currently, only the Hamburger Luftmessnetz is implemented.
