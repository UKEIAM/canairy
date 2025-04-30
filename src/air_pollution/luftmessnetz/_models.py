from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, field_serializer, Field

from ._typing import GroupCodes_T, Periods_T, TimeSpans_T, StationGroup_T


class BaseParams(BaseModel):
    pass

class _ActiveParam(BaseParams):
    active: bool | None = None

class _HiddenParam(BaseParams):
    include_hidden: bool | None = None

class ListParams(_ActiveParam, _HiddenParam):
    pass

class ItemListModel(BaseParams):
    @classmethod
    def from_response(cls, result: list[Any]) -> list[Self]:
        return [cls(**item) for item in result]



class Core(ItemListModel):
    code: str
    active: bool
    group: StationGroup_T
    name: str
    short_name: Annotated[str, Field(validation_alias="shortName")]
    description: str | None
    default_period: Annotated[str, Field(validation_alias="defaultPeriod")]
    periods: list[str]
    decimal_points: Annotated[int, Field(validation_alias="decimalPoints")]
    components: list[str]


class Threshold(ItemListModel):
    active: bool
    code: str
    component: str
    core: str
    name: str
    description: str | None
    value: float
    max_count: Annotated[int | None, Field(validation_alias="maxCount")]
    start: datetime | None


class DatetimeRangeParams(BaseParams):
    start: datetime | None = None
    end: datetime | None = None

    @field_serializer("start", "end")
    def custom_dt(self, dt: datetime) -> str:
        return dt.strftime("%d.%m.%Y %H:%M")


class ComponentParams(_ActiveParam):
    group_code: GroupCodes_T | None


class Station(ItemListModel):
    name: str
    code: str
    code_eu: Annotated[str, Field(validation_alias="codeEu")]
    address: str
    lat: str
    lng: str
    active: bool
    stationgroups: list[str]
    measuring_start: Annotated[
        datetime | None, Field(validation_alias="measuringStart")
    ]
    measuring_end: Annotated[datetime | None, Field(validation_alias="measuringEnd")]
    measuring_height: Annotated[int | None, Field(validation_alias="measuringHeight")]
    url: str
    information: str | None
    components: list[str]
    active_components: Annotated[list[str], Field(validation_alias="activeComponents")]
    partials: list
    lqis: list[str]
    exceeds: list[str]


class StationData(ItemListModel):
    datetime: datetime
    station: str
    core: str
    component: str
    period: Periods_T
    value: int


class ComponentDataParams(DatetimeRangeParams):
    stationgroup: str | None = None
    timespan: TimeSpans_T | None = None


class ComponentData(ItemListModel):
    datetime: datetime
    station: str
    core: str
    component: str
    period: Periods_T
    value: float | None


class Component(ItemListModel):
    code: str
    core: str
    period: str
    description: str | None
    unit: str
    min: int
    max: int
    decimal_points: Annotated[int, Field(validation_alias="decimalPoints")]


class StationDataParams(DatetimeRangeParams):
    period: Periods_T
    timespan: TimeSpans_T
    core: str | None
