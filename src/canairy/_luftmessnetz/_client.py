from datetime import datetime, timedelta
from typing import Any, ClassVar, TypeGuard, get_args

from .._http import build_client
from ._models import (
    BERLIN,
    BaseParams,
    Component,
    ComponentData,
    ComponentDataParams,
    ComponentParams,
    Core,
    ListParams,
    Station,
    StationData,
    StationDataParams,
    Threshold,
)
from ._typing import GroupCodes_T, Periods_T, TimeSpans_T

__all__ = ["LuftmessnetzClient"]


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


class LuftmessnetzClient:
    """Client for the luftmessnetz API shared by Hamburg and Berlin.

    Subclasses select the network by setting `BASE_URL`.
    """

    BASE_URL: ClassVar[str]

    def __init__(self) -> None:
        self._client = build_client()

    def get_components(
        self,
        *,
        active: bool | None = None,
        group_code: GroupCodes_T | None = None,
    ) -> list[Component]:
        """Retrieve component's metadata."""
        params = ComponentParams(active=active, group_code=group_code)
        return Component.from_response(self._get("components", params))

    def get_component_data(
        self,
        code: str,
        *,
        stationgroup: str | None = None,
        timespan: TimeSpans_T | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[ComponentData]:
        params = ComponentDataParams(
            stationgroup=stationgroup, timespan=timespan, start=start, end=end
        )
        # Component codes end in their period (no2_1h -> 1h); the API ignores
        # their case.
        suffix = code.rsplit("_", 1)[-1].lower()
        period = suffix if _is_period(suffix) else None
        result = self._get_data(f"components/{code}/data", params, period)
        return ComponentData.from_response(result)

    def get_cores(self) -> list[Core]:
        """Retrieve core metadata."""
        return Core.from_response(self._get("cores"))

    def get_thresholds(self) -> list[Threshold]:
        """Retrieve the thresholds for each each core."""
        return Threshold.from_response(self._get("exceeds"))

    def get_stations(
        self,
        *,
        active: bool | None = None,
        include_hidden: bool | None = None,
    ) -> list[Station]:
        """Retrieve a list of all measuring stations and their metadata."""
        params = ListParams(active=active, include_hidden=include_hidden)
        return Station.from_response(self._get("stations", params=params))

    def get_station(self, code: str) -> Station:
        """Retrieve metadata of a single station."""
        return Station(**self._get(f"stations/{code}"))

    def get_station_data(
        self,
        station_code: str,
        *,
        period: Periods_T,
        timespan: TimeSpans_T,
        start: datetime | None = None,
        end: datetime | None = None,
        core: str | None = None,
    ) -> list[StationData]:
        params = StationDataParams(
            period=period, timespan=timespan, start=start, end=end, core=core
        )
        return StationData.from_response(
            self._get_data(f"stations/{station_code}/data", params, period)
        )

    def _get_data(
        self,
        endpoint: str,
        params: ComponentDataParams | StationDataParams,
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

    def _get(self, endpoint: str, params: BaseParams | None = None) -> Any:
        params_ = params.model_dump(exclude_none=True) if params else None
        rsp = self._client.get(self._url(endpoint), params=params_)
        return rsp.raise_for_status().json()

    def _url(self, endpoint: str) -> str:
        return f"{self.BASE_URL}/{endpoint}"



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
