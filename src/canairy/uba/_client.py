import datetime
from typing import Any, Literal

from .._http import UBA_RETRY_STATUSES, build_client
from ._models import BaseParams
from ._typing import Language, Usage
from .components import UBAComponentsGetParams, UBAComponentsGetResponse
from .measures import UBAMeasuresGetRequestParams
from .measures._models import UBAMeasuresGetResponse
from .networks import UBANetworksGetParams, UBANetworksGetResponse
from .scopes import UBAScopesGetParams, UBAScopesGetResponse
from .stations import UBAStationGetParmas, UBAStationGetResponse
from .thresholds import UBAThresholdsGetParams, UBAThresholdsGetResponse

__all__ = ["UBAClient"]


class UBAClient:
    BASE_URL = "https://luftdaten.umweltbundesamt.de/api/air-data/v4"

    def __init__(self) -> None:
        self._client = build_client(UBA_RETRY_STATUSES)

    def get_stations(
        self,
        usage: Usage = None,
        dt_start: datetime.datetime | None = None,
        dt_stop: datetime.datetime | None = None,
        lang: Language = None,
    ) -> UBAStationGetResponse:
        params = UBAStationGetParmas.from_dt(usage, dt_start, dt_stop, lang)
        response = self._get("stations", params=params)
        return UBAStationGetResponse.from_response(response)

    def get_components(self, lang: Language = None) -> UBAComponentsGetResponse:
        """Load a table of all available air pollutants (components) including
        meta data.

        Params:
            lang: Language of component description. Default 'en'

        Returns:
            Componets response model.
        """

        params = UBAComponentsGetParams(lang=lang)
        response = self._get("components", params=params)
        return UBAComponentsGetResponse.from_response(response)

    def get_scopes(self, lang: Language = None) -> UBAScopesGetResponse:
        params = UBAScopesGetParams(lang=lang)
        response = self._get("scopes", params=params)
        return UBAScopesGetResponse.from_response(response)

    def get_measures(
        self,
        dt_start: datetime.datetime,
        dt_stop: datetime.datetime,
        station: int | str,
        component: int,
        scope: int,
    ) -> UBAMeasuresGetResponse:
        params = UBAMeasuresGetRequestParams.from_dt(
            dt_start=dt_start,
            dt_stop=dt_stop,
            station=station,
            component=component,
            scope=scope,
        )
        response = self._get("measures", params=params)
        return UBAMeasuresGetResponse.from_response(response)

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

    def get_thresholds(
        self, use: Literal["airquality", "measure"], component_id: int, scope_id: int
    ) -> UBAThresholdsGetResponse:
        """Get the thresholds of a component/scope combination.

        Args:
            use:            Specific usecase
            component_id:   compnent_id
            scope_id:       scope_id

        Returns:
            Thresholds response model.
        """
        params = UBAThresholdsGetParams(use=use, component=component_id, scope=scope_id)
        response = self._get("thresholds", params)
        return UBAThresholdsGetResponse.from_response(response)

    def _get(self, endpoint: str, params: BaseParams | None = None) -> Any:
        params_ = params.model_dump(exclude_none=True) if params else None
        # 429 and 5xx are retried by the transport; raise what is left.
        rsp = self._client.get(self._url(endpoint), params=params_)
        return rsp.raise_for_status().json()

    def _url(self, endpoint: str) -> str:
        return f"{UBAClient.BASE_URL}/{endpoint}/json"

