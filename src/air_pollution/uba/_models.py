import datetime
from typing import Any, Self
from pydantic import BaseModel

from ._typing import Language, Usage, Timestamp, StrDict, Index


class BaseParams(BaseModel):
    pass

class BaseResponse(BaseModel):
    pass


class GetStationParams(BaseParams):
    usage: Usage = None
    date_from: datetime.date | None = None
    time_from: int | None = None
    date_to: datetime.date | None = None
    time_to: int | None = None
    lang: Language = None

    @classmethod
    def from_dt(
        cls,
        usage: Usage,
        dt_start: Timestamp | None,
        dt_stop: Timestamp | None,
        lang: Language,
    ) -> Self:
        if isinstance(dt_start, datetime.datetime):
            date_from = dt_start.date()
            time_from = int(dt_start.strftime("%H")) + 1
        elif isinstance(dt_start, datetime.date):
            date_from = dt_start
            time_from = None
        elif dt_start is None:
            date_from = None
            time_from = None
        else:
            raise TypeError("`dt_start` not a valid `Timestamp`")


        if isinstance(dt_stop, datetime.datetime):
            date_to = dt_stop.date()
            time_to = int(dt_stop.strftime("%H")) + 1
        elif isinstance(dt_stop, datetime.date):
            date_to = dt_stop
            time_to = None
        elif dt_start is None:
            date_to = None
            time_to = None
        else:
            raise TypeError("`dt_stop` not a valid `Timestamp`")

        return cls(
            usage=usage,
            lang=lang,
            date_from=date_from,
            date_to=date_to,
            time_from=time_from,
            time_to=time_to,
        )


class ItemListModel(BaseModel):
    @classmethod
    def from_response(cls, result: list[Any]) -> list[Self]:
        return [cls(**item) for item in result]


class StationType(BaseModel):
    id: int
    name: str


class StationNetwork(BaseModel):
    id: int
    code: str
    name: str


class StationSetting(BaseModel):
    id: int
    name: str
    short_name: str


class StationLocation(BaseModel):
    street: str
    street_nr: str
    zip_code: str
    city: str
    longitude: str
    latitude: str

from typing import Union

class Station(BaseModel):
    id: int
    code: str
    name: str
    synonym: str
    active_from: datetime.date
    active_to: datetime.date | None
    type: StationType
    network: StationNetwork
    setting: StationSetting

    @classmethod
    def from_flat_dict(cls, raw: StrDict) -> Self:
        root: dict[str, Union[str | StrDict]] = {}
        sm_type: StrDict = {}
        sm_setting: StrDict = {}
        sm_network: StrDict = {}
        sm_location: StrDict = {}

        for key, val in raw.items():
            if key.startswith("type "):
                sm_type[key.removeprefix("type ")] = val
            elif key.startswith("network "):
                sm_network[key.removeprefix("network ")] = val
            elif key.startswith("setting "):
                sm_setting[key.removeprefix("setting ").replace(" ", "_")] = val
            elif key in [
                "street",
                "street nr",
                "zip code",
                "city",
                "latitude",
                "longitude",
            ]:
                sm_location[key.replace(" ", "_")] = val
            else:
                root[key.replace(" ", "_")] = val
        root['type'] = sm_type
        root['setting'] = sm_setting
        root['network'] = sm_network
        root['location'] = sm_location
        return cls(**root)


class UBAResponseRequest(BaseModel):
    recent: bool
    index: str
    lang: Language


class UBAStationGetResponse(BaseModel):
    request: UBAResponseRequest
    indices: list[str]
    data: list[Station]

    @classmethod
    def from_response(cls, response: Any) -> Self:
        indices = list(map(lambda x: x.removeprefix("station "), response["indices"]))
        data = [
            Station.from_flat_dict({k: v for (k, v) in zip(indices, item)})
            for item in response["data"].values()
        ]
        return cls(request=response["request"], indices=indices, data=data)
