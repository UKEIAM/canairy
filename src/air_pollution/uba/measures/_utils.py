import datetime
import polars as pl
from ._models import Measurement


def convert_request_data(data: dict[str, dict[str, list[str]]]):
    items = []
    for station, timeframes in data.items():
        for date_start, values in timeframes.items():
            mm = Measurement.from_list(values)
            item = mm.model_dump()
            item['date_start'] = date_start
            item['station_id'] = int(station)
            items.append(item)
    return pl.DataFrame(items).select(['date_start', 'date_end', 'station_id', 'component_id', 'scope_id', 'index', 'value'])




