from datetime import datetime, timedelta
import time
from typing import Any, TypeGuard, get_args
import logging

from hishel.httpx import SyncCacheClient
import httpx
from ratelimit import limits, sleep_and_retry

from ._models import (
    BERLIN,
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

# The API silently moves a custom start forward to `end - limit` (both ends
# inclusive, local calendar days). Periods not listed here are not split.
# The limits are fixed day counts, not calendar months: end 06.03.2025 moves
# start to 03.02.2025, and 31 days ending after February are returned whole.
RANGE_LIMITS: dict[Periods_T, timedelta] = {
    "1h": timedelta(days=31),
    "8hg": timedelta(days=31),
    "24hg": timedelta(days=31),
    "24h": timedelta(days=365),
}


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
        # Component codes end in their period (no2_1h -> 1h); the API ignores
        # their case.
        suffix = code.rsplit("_", 1)[-1].lower()
        period = suffix if _is_period(suffix) else None
        result = self._get_data(f"components/{code}/data", params, period)
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
            self._get_data(f"stations/{station_code}/data", params, period)
        )

    def _get_data(
        self,
        endpoint: str,
        params: HHComponentDataParams | HHStationDataParams,
        period: Periods_T | None,
    ) -> list[Any]:
        """Request custom ranges in windows the API does not truncate.

        `period` selects the window size; it is only needed for custom ranges.
        """
        # The API ignores start/end unless timespan is "custom".
        if params.start is not None or params.end is not None:
            if params.timespan is None:
                params = params.model_copy(update={"timespan": "custom"})
            elif params.timespan != "custom":
                raise ValueError(
                    f'start/end require timespan="custom", got {params.timespan!r}'
                )
        if params.timespan != "custom" or params.start is None:
            return self._get(endpoint, params)
        if period is None:
            raise ValueError(
                f"Cannot split a custom range of {endpoint!r}: unknown period"
            )

        # The API defaults a missing end to its local now; make that explicit
        # so the range gets split.
        range_end = params.end or datetime.now(BERLIN).replace(tzinfo=None)
        # The API answers an inverted range with no rows, and ignores a start
        # after its now if end is missing.
        if params.start > range_end:
            if params.end is not None:
                raise ValueError(f"start {params.start} is after end {params.end}")
            return []
        rows: list[Any] = []
        shared: set[tuple[str, str, str]] = set()
        # Each response is sorted by datetime, newest first, across all
        # stations and components, so joining windows newest first keeps a
        # global order.
        for start, end in reversed(split_range(params.start, range_end, period)):
            window = params.model_copy(update={"start": start, "end": end})
            response = self._get(endpoint, window)
            rows += [row for row in response if _row_key(row) not in shared]
            # Consecutive windows share their boundary timestamp: only rows at
            # this window's oldest timestamp can repeat in the next one.
            oldest = response[-1]["datetime"] if response else None
            shared = {_row_key(row) for row in response if row["datetime"] == oldest}
        return rows

    @sleep_and_retry
    @limits(120, period=60)
    def _get(self, endpoint: str, params: BaseParams | None = None) -> Any:
        params_ = params.model_dump(exclude_none=True) if params else None
        return (
            backoff(self._client.get, self._url(endpoint), params=params_)
            .raise_for_status()
            .json()
        )

    def _url(self, endpoint: str) -> str:
        return f"{HHClient.BASE_URL}/{endpoint}"



def backoff(func, *args, **kwargs) -> Any:   # type: ignore
    base = 2
    for i in range(1, MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except httpx.RemoteProtocolError:
            logger.debug(f"RemoteProtocolError: retry {i}")
            time.sleep(base**i)
    # The last attempt (the only one if MAX_RETRIES <= 1) raises its error.
    return func(*args, **kwargs)


def _row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (row["datetime"], row["station"], row["component"])


def _is_period(value: str) -> TypeGuard[Periods_T]:
    return value in get_args(Periods_T)


def split_range(
    start: datetime, end: datetime, period: Periods_T
) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into windows the API returns without truncation.

    Consecutive windows share their boundary timestamp.
    """
    limit = RANGE_LIMITS.get(period)
    if limit is None:
        return [(start, end)]
    windows = []
    while end - start > limit:
        windows.append((start, start + limit))
        start += limit
    windows.append((start, end))
    return windows
