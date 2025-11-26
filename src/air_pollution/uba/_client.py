import logging
import time
from typing import Any

import hishel
import httpx
from ratelimit import limits, sleep_and_retry

from ._models import BaseParams, GetStationParams, UBAStationGetResponse
from ._typing import Usage, Language, Timestamp

__all__ = ["UBAClient"]

logger = logging.getLogger(__name__)
LOG_FMT = "%(levelname)-10s %(message)s"
MAX_RETRIES = 8


class UBAClient:
    BASE_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v4"

    def __init__(self) -> None:
        self._client = hishel.CacheClient()

    def get_stations(
        self,
        usage: Usage = None,
        dt_start: Timestamp = None,
        dt_stop: Timestamp = None,
        lang: Language = None,
    ) -> UBAStationGetResponse:
        params = GetStationParams.from_dt(usage, dt_start, dt_stop, lang)
        response = self._get("stations", params=params)
        return UBAStationGetResponse.from_response(response)

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
        return f"{UBAClient.BASE_URL}/{endpoint}/json"


def backoff(func, *args, **kwargs) -> Any:  # type: ignore
    base = 2
    for i in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except httpx.RemoteProtocolError:
            logging.debug(f"RemoteProtoclolError: retry {i}")
            timeout = base**i
            time.sleep(timeout)
