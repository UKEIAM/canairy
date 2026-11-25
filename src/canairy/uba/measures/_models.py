import datetime
from collections.abc import Sequence
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator

from .._models import BaseParams, BaseResponse
from .._typing import Index, Language
from ..utils import normalize_response_indices

RawDataSeq = Sequence[int | float | str | None]


class UBAMeasuresGetRequestParams(BaseParams):
    date_from: datetime.date
    time_from: int = Field(ge=1, le=24)
    date_to: datetime.date
    time_to: int = Field(ge=1, le=24)
    station: int | str
    component: int
    scope: int

    @classmethod
    def from_dt(
        cls,
        dt_start: datetime.datetime,
        dt_stop: datetime.datetime,
        station: int | str,
        component: int,
        scope: int,
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
            scope=scope,
        )


class UBAMeasuresGetResponseRequest(BaseResponse):
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

    @field_validator("time_to", "time_from", mode="before")
    @classmethod
    def _hour_string_to_time(cls, val: str) -> datetime.time:
        h, m, s = (int(x) for x in val.split(":"))
        return datetime.time(h - 1, m, s)


class Measurement(BaseModel):
    date_start: datetime.datetime
    date_end: datetime.datetime
    station_id: int
    component_id: int
    scope_id: int
    value: float | None
    index: int | None

    @classmethod
    def from_list(
        cls, keys: list[str], values: RawDataSeq, date_start: str, station: int
    ) -> Self:
        items = {key: val for key, val in zip(keys, values, strict=True)}
        items["date_start"] = date_start
        items["station_id"] = station
        return cls(**items)

    @field_validator("date_end", mode="before")
    @classmethod
    def _fix_end_date(cls, val: str) -> datetime.datetime:
        date, time = val.split(" ")
        parsed_date = datetime.date(*(int(x) for x in date.split("-")))
        h, m, s = (int(x) for x in time.split(":"))
        if h == 24:
            h = 0
            parsed_date += datetime.timedelta(days=1)
        return datetime.datetime(
            parsed_date.year, parsed_date.month, parsed_date.day, h, m, s
        )


class UBAMeasuresGetResponse(BaseResponse):
    request: UBAMeasuresGetResponseRequest
    indices: dict[str, dict[str, dict[str, list[str]]]]
    data: list[Measurement]

    @classmethod
    def from_response(cls, response: Any) -> Self:
        request = UBAMeasuresGetResponseRequest(**response["request"])
        indices = response["indices"]
        data = cls.convert_request_data(
            normalize_response_indices(indices), response["data"]
        )
        return cls(request=request, indices=indices, data=data)

    @staticmethod
    def convert_request_data(
        indices: list[str], data: dict[str, Any]
    ) -> Sequence[Measurement]:
        items = []
        for station, timeframes in data.items():
            for date_start, values in timeframes.items():
                mm = Measurement.from_list(indices, values, date_start, int(station))
                items.append(mm)
        return items


EXPECTED_MEASURES_LIMITS_INDICES = [
    "scope id",
    "component id",
    "station id",
    "limit date start min",
    "limit date start max",
]


class UBAMeasuresLimit(BaseModel):
    """First and last measurement start of one scope/component/station."""

    scope_id: int
    component_id: int
    station_id: int
    date_start_min: datetime.datetime
    date_start_max: datetime.datetime

    @classmethod
    def from_list_item(cls, item: RawDataSeq) -> Self:
        return cls(**dict(zip(cls.model_fields.keys(), item, strict=True)))

    def overlaps(self, start: datetime.datetime, end: datetime.datetime) -> bool:
        """True if measurements may exist with a start time in [start, end]."""
        return self.date_start_min <= end and self.date_start_max >= start


class UBAMeasuresLimitsGetResponse(BaseResponse):
    indices: list[str]
    data: list[UBAMeasuresLimit]

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> Self:
        indices = next(iter(response["indices"].values()))
        if indices != EXPECTED_MEASURES_LIMITS_INDICES:
            raise ValueError(
                "Unexpected column order in UBA measures limits response: "
                f"got {indices!r}, expected {EXPECTED_MEASURES_LIMITS_INDICES!r}"
            )
        data = [
            UBAMeasuresLimit.from_list_item(item)
            for item in cls.iter_response_data(response)
        ]
        return cls(indices=indices, data=data)

    def lookup(self) -> dict[tuple[int, int, int], UBAMeasuresLimit]:
        """Index limits by ``(station_id, component_id, scope_id)``."""
        return {
            (lim.station_id, lim.component_id, lim.scope_id): lim for lim in self.data
        }
