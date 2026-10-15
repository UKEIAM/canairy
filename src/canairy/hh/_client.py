from datetime import datetime
import json
import time
from typing import Any
import logging

from hishel.httpx import SyncCacheClient
import httpx
from ratelimit import limits, sleep_and_retry

from httpx._types import QueryParamTypes

from ._models import (
    BaseParams,
    HHComponent,
    HHComponentParams,
    HHComponentData,
    HHComponentDataParams,
    HHCore,
    HHStation,
    HHStationDataParams,
    HHThreshold,
    HHListParams,
    HHStationData,
)

from ._typing import GroupCodes_T, TimeSpans_T, Periods_T

__all__ = ["HHClient"]

logger = logging.getLogger(__name__)
MAX_RETRIES = 8


class HHClient:
    BASE_URL = "https://hamburg.luftmessnetz.de/api"

    def __init__(self) -> None:
        self._client = SyncCacheClient(timeout=60)

    def get_components(
        self,
        *,
        active: bool | None = None,
        group_code: GroupCodes_T | None = None,
    ) -> list[HHComponent]:
        """Retrieve component's metadata."""
        params = HHComponentParams(active=active, group_code=group_code)
        return HHComponent.from_response(self._get("components", params))

    def get_component_data(
        self,
        code: str,
        *,
        stationgroup: str | None = None,
        timespan: TimeSpans_T | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[HHComponentData]:
        params = HHComponentDataParams(
            stationgroup=stationgroup, timespan=timespan, start=start, end=end
        )
        result = self._get(f"components/{code}/data", params)
        return HHComponentData.from_response(result)

    def get_cores(self) -> list[HHCore]:
        """Retrieve core metadata."""
        return HHCore.from_response(self._get("cores"))

    def get_thresholds(self) -> list[HHThreshold]:
        """Retrieve the thresholds for each each core."""
        return HHThreshold.from_response(self._get("exceeds"))

    def get_stations(
        self,
        *,
        active: bool | None = None,
        include_hidden: bool | None = None,
    ) -> list[HHStation]:
        """Retrieve a list of all measuring stations and their metadata."""
        params = HHListParams(active=active, include_hidden=include_hidden)
        return HHStation.from_response(self._get("stations", params=params))

    def get_station(self, code: str) -> HHStation:
        """Retrieve metadata of a single station."""
        return HHStation(**self._get(f"stations/{code}"))

    def get_station_data(
        self,
        station_code: str,
        *,
        period: Periods_T,
        timespan: TimeSpans_T,
        start: datetime | None = None,
        end: datetime | None = None,
        core: str | None = None,
    ) -> list[HHStationData]:
        params = HHStationDataParams(
            period=period, timespan=timespan, start=start, end=end, core=core
        )
        return HHStationData.from_response(
            self._get(f"stations/{station_code}/data", params)
        )

    @sleep_and_retry
    @limits(120, period=60)
    def _get(self, endpoint: str, params: BaseParams | None = None) -> Any:
        params_ = params.model_dump(exclude_none=True) if params else None
        meta = self._client.head(self._url(endpoint), params=params_).raise_for_status()

        if (meta.headers.get("Transfer-Encoding") == "chunked") or (
            "content-length" not in meta.headers
        ):
            logger.debug("Streaming response")
            return backoff(self._stream, self._url(endpoint), params=params_)

        logger.debug("Non-streaming response")
        return (
            backoff(self._client.get, self._url(endpoint), params=params_)
            .raise_for_status()
            .json()
        )

    def _stream(
        self,
        endpoint: str,
        *,
        params: QueryParamTypes | None = None,
        method: str = "GET",
    ) -> Any:
        with self._client.stream(method, endpoint, params=params) as stream:
            stream.raise_for_status()
            buff = json.loads("".join(data for data in stream.iter_text()))
        return buff

    def _url(self, endpoint: str) -> str:
        return f"{HHClient.BASE_URL}/{endpoint}"



def backoff(func, *args, **kwargs) -> Any:   # type: ignore
    base = 2
    for i in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except httpx.RemoteProtocolError:
            logger.debug(f"RemoteProtocolError: retry {i}")
            timeout = base**i
            time.sleep(timeout)
