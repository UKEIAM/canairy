import datetime
from typing import Any, Self

from pydantic import BaseModel, field_validator, Field
import polars as pl

from .._models import BaseParams, BaseResponse
from .._typing import Index, Language


class MeasuresGetRequestParams(BaseParams):
    date_from: datetime.date
    time_from: int = Field(ge=1, le=24)
    date_to: datetime.date
    time_to: int = Field(ge=1, le=24)
    station: int | str | None = None
    component: int | None = None
    scope: int | None = None

    @classmethod
    def from_dt(
        cls,
        dt_start: datetime.datetime,
        dt_stop: datetime.datetime,
        station: int | str | None = None,
        component: int | None = None,
        scope: int | None = None
    ) -> Self:
        if isinstance(dt_start, datetime.datetime):
            date_from = dt_start.date()
            time_from = int(dt_start.strftime("%H")) + 1
        else:
            raise TypeError("`dt_start` not a valid `datetime`")


        if isinstance(dt_stop, datetime.datetime):
            date_to = dt_stop.date()
            time_to = int(dt_stop.strftime("%H")) + 1
        else:
            raise TypeError("`dt_stop` not a valid `datetime`")

        return cls(
            date_from=date_from,
            date_to=date_to,
            time_from=time_from,
            time_to=time_to,
            station=station,
            component=component,
            scope=scope
        )

class MeasuresGetResponseRequest(BaseResponse):
    component: str | None = None
    station: str | None = None
    date_from: datetime.date
    date_to: datetime.date
    time_from: datetime.time
    time_to: datetime.time
    index: Index | None = None
    lang: Language | None = None
    datetime_from: datetime.datetime
    datetime_to: datetime.datetime

    @field_validator('time_to', 'time_from', mode="before")
    @classmethod
    def _hour_string_to_time(cls, val: str) -> datetime.time:
        h, m, s = map(lambda x: int(x), val.split(":"))
        return datetime.time(h-1, m, s)



class Measurement(BaseModel):
    component_id: int
    scope_id: int
    value: float | None
    date_end: datetime.datetime
    index: int | None
    date_start: datetime.datetime
    station_id: int

    @classmethod
    def from_list(cls, values: list[int |float|str], date_start, station: int) -> Self:
        item = {k: v for (k, v) in zip(cls.model_fields.keys(), values)}
        item['date_start'] = date_start
        item['station_id'] = station
        return cls(**item)

    @field_validator('date_end', mode="before")
    @classmethod
    def _fix_end_date(cls, val: str) -> datetime.datetime:
        date, time = val.split(" ")
        parsed_date = datetime.date(*map(lambda x: int(x), date.split("-")))
        h, m, s = map(lambda x: int(x), time.split(":"))
        if h == 24:
            h = 0
            parsed_date += datetime.timedelta(days=1)
        return datetime.datetime(parsed_date.year, parsed_date.month, parsed_date.day, h, m, s)



class MeasuresGetResponse(BaseResponse):
    request: MeasuresGetResponseRequest
    indices: dict[str, dict[str, dict[str, list[str]]]]
    data: list[Measurement]

    @classmethod
    def from_response(cls, response: Any) -> Self:
        request = MeasuresGetResponseRequest(**response['request'])
        indices = response['indices']
        data = convert_request_data(response['data'])
        return cls(request=request, indices=indices, data=data)

    
def convert_request_data(data: dict[str, dict[str, list[str]]]):
    items = []
    for station, timeframes in data.items():
        for date_start, values in timeframes.items():
            mm = Measurement.from_list(values, date_start, int(station))
            items.append(mm)
    return items

