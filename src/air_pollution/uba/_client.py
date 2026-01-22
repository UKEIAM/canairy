import datetime
import logging
import time
from typing import Any

import httpx
from hishel.httpx import SyncCacheClient
from ratelimit import limits, sleep_and_retry

from ._models import BaseParams
from ._typing import Language, Timestamp, Usage
from .components import ComponentsGetParams, ComponentsGetResponse
from .measures import MeasuresGetRequestParams
from .measures._models import MeasuresGetResponse
from .networks import UBANetworksGetParams, UBANetworksGetResponse
from .scopes import ScopesGetParams, ScopesGetResponse
from .stations import GetStationParams, UBAStationGetResponse

__all__ = ["UBAClient"]

logger = logging.getLogger(__name__)
MAX_RETRIES = 8


class UBAClient:
    BASE_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v4"

    def __init__(self) -> None:
        self._client = SyncCacheClient(timeout=60)

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

    def get_components(self, lang: Language = None) -> ComponentsGetResponse:
        """Load a table of all available air pollutants (components) including
        meta data.

        Params:
            lang: Language of component description. Default 'en'

        Returns:
            Componets response model.
        """

        params = ComponentsGetParams(lang=lang)
        response = self._get("components", params=params)
        # sp_model = create_components_get_response_model(response)
        return ComponentsGetResponse.from_response(response)

    def get_scopes(self, lang: Language = None) -> ScopesGetResponse:
        params = ScopesGetParams(lang=lang)
        response = self._get("scopes", params=params)
        return ScopesGetResponse.from_response(response)

    def get_measures(
        self,
        dt_start: datetime.datetime,
        dt_stop: datetime.datetime,
        station: int | str | None = None,
        component: int | None = None,
        scope: int | None = None,
    ) -> MeasuresGetResponse:
        params = MeasuresGetRequestParams.from_dt(
            dt_start=dt_start,
            dt_stop=dt_stop,
            station=station,
            component=component,
            scope=scope,
        )
        response = self._get("measures", params=params)
        return MeasuresGetResponse.from_response(response)

    def get_networks(self, lang: Language | None = None) -> UBANetworksGetResponse:
        """Get a list of all air qualityt measurement networks.

        Args:
            lang:   Description languange. Default 'en'.

        Returns:
            Networks response model.
        """
        params = UBANetworksGetParams(lang=lang)
        response = self._get("networks", params=params)
        return UBANetworksGetResponse.from_response(response)

    @sleep_and_retry  # type: ignore
    @limits(120, period=60)  # type: ignore
    def _get(self, endpoint: str, params: BaseParams | None = None) -> Any:
        params_ = params.model_dump(exclude_none=True) if params else None

        rsp = backoff(self._client.get, self._url(endpoint), params=params_)
        return rsp.json()

    def _url(self, endpoint: str) -> str:
        return f"{UBAClient.BASE_URL}/{endpoint}/json"


def backoff(func, *args, **kwargs) -> Any:  # type: ignore
    base = 2
    for i in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs).raise_for_status()
        except httpx.RemoteProtocolError:
            logging.debug(f"RemoteProtoclolError: retry {i}")
            timeout = base**i
            time.sleep(timeout)
        except httpx.HTTPStatusError:
            logging.debug(f"RemoteProtoclolError: retry {i}")
            timeout = base**i
            time.sleep(timeout)
