from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, ClassVar

from .._http import build_client
from ._models import (
    AQI_COLUMNS,
    EXCEEDANCE_COLUMNS,
    MEASUREMENT_COLUMNS,
    OZONE_WARNING_COLUMNS,
    REFERENCE_MEASUREMENT_COLUMNS,
    TOTAL_AQI_COLUMNS,
    Aggregation,
    AirQualityIndex,
    Availability,
    BaseParams,
    BasisParams,
    Component,
    DateMeasurementParams,
    DatetimeMeasurementParams,
    ExceedanceDays,
    FilterParams,
    IdList,
    LimitsParams,
    Matrix,
    Measurement,
    Method,
    OzoneWarning,
    OzoneWarningParams,
    Station,
    StationParams,
    TotalAirQualityIndex,
    Unit,
    YearParams,
)

__all__ = ["NRWClient"]

# The API's answer (HTTP 200) when a query matches nothing.
NO_MATCH = "Keine passenden Einträge gefunden"


class NRWClient:
    """LANUK Nordrhein-Westfalen, documented at luftqualitaet.nrw.de/apidoku.php.

    Stations, components, methods, matrices, units and aggregations are
    referenced by numeric id; look them up with the `get_*` metadata methods.
    Measurement methods return the intervals that lie completely within
    [start, end]. All arguments taking ids also accept a sequence of ids.
    """

    BASE_URL: ClassVar[str] = "https://luftqualitaet.nrw.de/api"

    def __init__(self) -> None:
        self._client = build_client()

    # --- metadata (basis.php) ---------------------------------------------------

    def get_components(self) -> list[Component]:
        return [Component(**c) for c in self._basis("komponente")]

    def get_methods(self) -> list[Method]:
        return [Method(**m) for m in self._basis("methode")]

    def get_matrices(self) -> list[Matrix]:
        return [Matrix(**m) for m in self._basis("matrix")]

    def get_units(self) -> list[Unit]:
        return [Unit(**u) for u in self._basis("einheit")]

    def get_aggregations(self) -> list[Aggregation]:
        return [Aggregation(**a) for a in self._basis("aggregation")]

    def get_station_classes(self) -> list[str]:
        return list(self._basis("stationsklasse"))

    def get_station_environments(self) -> list[str]:
        return list(self._basis("stationsumgebung"))

    def get_stations(
        self,
        *,
        station: IdList | None = None,
        code: str | Sequence[str] | None = None,
        eu_code: str | Sequence[str] | None = None,
        component: IdList | None = None,
        aggregation: IdList | None = None,
        station_class: str | Sequence[str] | None = None,
        environment: str | Sequence[str] | None = None,
        include_components: bool = False,
    ) -> list[Station]:
        """List stations (incl. closed ones), filtered by all given arguments.

        `include_components` adds each station's series with their data range.
        """
        params = StationParams(
            station=station,
            stationkuerzel=code,
            eucode=eu_code,
            komponente=component,
            aggregation=aggregation,
            stationsklasse=station_class,
            stationsumgebung=environment,
            komponentenliste="id" if include_components else "nein",
        )
        return [Station(**s) for s in self._get("station", params)]

    def get_availability(
        self,
        *,
        station: IdList | None = None,
        component: IdList | None = None,
        aggregation: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Availability]:
        """First and last day with data per series (limits.php).

        Without `start`, the API only looks at the last 5 months; `end`
        defaults to today and requires `start`.
        """
        if end is not None and start is None:
            raise ValueError("end requires start")
        params = LimitsParams(
            station=station,
            komponente=component,
            aggregation=aggregation,
            methode=method,
            matrix=matrix,
            beginn=start,
            ende=end,
        )
        return [Availability(**a) for a in self._get("limits", params)]

    # --- measurements -----------------------------------------------------------

    def get_hourly(
        self,
        component: IdList,
        start: datetime,
        end: datetime,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Hourly means (aggregation 1); available from 2019-12-31."""
        return self._datetime_measurements(
            "stundenmittelwerte", component, start, end, station, method, matrix
        )

    def get_moving_8h(
        self,
        component: IdList,
        start: datetime,
        end: datetime,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Moving 8-hour means (aggregation 2); only ozone (component 1)."""
        return self._datetime_measurements(
            "g8stundenmittelwerte", component, start, end, station, method, matrix
        )

    def get_daily(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Daily means (aggregation 4); `end` is exclusive."""
        return self._date_measurements(
            "tagesmittelwerte", component, start, end, station, method, matrix
        )

    def get_daily_sums(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Daily sums (aggregation 7), e.g. precipitation; `end` is exclusive."""
        return self._date_measurements(
            "tagessummenwerte", component, start, end, station, method, matrix
        )

    def get_daily_8h_max(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Daily maximum 8-hour mean (aggregation 16); only ozone."""
        return self._date_measurements(
            "8stundenmaxima", component, start, end, station, method, matrix,
            reference=True,
        )

    def get_4day(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """4-day means of samplers (aggregation 27), e.g. benzene."""
        return self._date_measurements(
            "4tagesmittelwerte", component, start, end, station, method, matrix
        )

    def get_monthly(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Monthly means (aggregation 5) of the months within [start, end)."""
        return self._date_measurements(
            "monatsmittelwerte", component, start, end, station, method, matrix,
            reference=True,
        )

    def get_monthly_sums(
        self,
        component: IdList,
        start: date,
        end: date,
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Monthly sums (aggregation 8) of the months within [start, end)."""
        return self._date_measurements(
            "monatssummenwerte", component, start, end, station, method, matrix,
            reference=True,
        )

    def get_yearly(
        self,
        component: IdList,
        years: int | Sequence[int],
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Yearly means (aggregation 6)."""
        return self._year_measurements(
            "jahresmittelwerte", component, years, station, method, matrix
        )

    def get_yearly_sums(
        self,
        component: IdList,
        years: int | Sequence[int],
        *,
        station: IdList | None = None,
        method: IdList | None = None,
        matrix: IdList | None = None,
    ) -> list[Measurement]:
        """Yearly sums (aggregation 9)."""
        return self._year_measurements(
            "jahressummenwerte", component, years, station, method, matrix
        )

    def get_pm10_exceedance_days(
        self,
        years: int | Sequence[int],
        *,
        station: IdList | None = None,
        method: IdList | None = None,
    ) -> list[ExceedanceDays]:
        """Days per year with a PM10 daily mean above 50 µg/m³.

        For the current year, the count runs up to the end of the last
        evaluated month.
        """
        params = YearParams(jahr=years, station=station, methode=method)
        return ExceedanceDays.from_rows(
            self._get("pm10uetage", params), EXCEEDANCE_COLUMNS
        )

    # --- indices and warnings -----------------------------------------------------

    def get_air_quality_index(
        self,
        component: IdList,
        start: datetime,
        end: datetime,
        *,
        station: IdList | None = None,
    ) -> list[AirQualityIndex]:
        """Hourly index per pollutant: PM10 (200), PM2.5 (201), NO2 (3), SO2 (2), O3 (1)."""
        params = _datetime_params(component, start, end, station)
        return AirQualityIndex.from_rows(self._get("lqindex", params), AQI_COLUMNS)

    def get_total_air_quality_index(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        *,
        station: IdList | None = None,
    ) -> list[TotalAirQualityIndex]:
        """Hourly overall index; without a range, the last available hour."""
        if (start is None) != (end is None):
            raise ValueError("start and end must be given together")
        if start is not None and end is not None:
            params: BaseParams = _datetime_params(None, start, end, station)
        else:
            params = FilterParams(station=station)
        return TotalAirQualityIndex.from_rows(
            self._get("gesamtlqindex", params), TOTAL_AQI_COLUMNS
        )

    def get_ozone_warnings(self, day: date | None = None) -> list[OzoneWarning]:
        """Ozone messages for `day`; by default today and the next two days."""
        params = OzoneWarningParams(bezugszeit=day)
        return OzoneWarning.from_rows(
            self._get("ozonwarnung", params), OZONE_WARNING_COLUMNS
        )

    # --- internals ----------------------------------------------------------------

    def _datetime_measurements(
        self,
        endpoint: str,
        component: IdList,
        start: datetime,
        end: datetime,
        station: IdList | None,
        method: IdList | None,
        matrix: IdList | None,
    ) -> list[Measurement]:
        params = _datetime_params(component, start, end, station, method, matrix)
        return Measurement.from_rows(self._get(endpoint, params), MEASUREMENT_COLUMNS)

    def _date_measurements(
        self,
        endpoint: str,
        component: IdList,
        start: date,
        end: date,
        station: IdList | None,
        method: IdList | None,
        matrix: IdList | None,
        reference: bool = False,
    ) -> list[Measurement]:
        _check_range(start, end)
        params = DateMeasurementParams(
            komponente=component,
            beginn=start,
            ende=end,
            station=station,
            methode=method,
            matrix=matrix,
        )
        columns = REFERENCE_MEASUREMENT_COLUMNS if reference else MEASUREMENT_COLUMNS
        return Measurement.from_rows(self._get(endpoint, params), columns)

    def _year_measurements(
        self,
        endpoint: str,
        component: IdList,
        years: int | Sequence[int],
        station: IdList | None,
        method: IdList | None,
        matrix: IdList | None,
    ) -> list[Measurement]:
        params = YearParams(
            komponente=component,
            jahr=years,
            station=station,
            methode=method,
            matrix=matrix,
        )
        return Measurement.from_rows(
            self._get(endpoint, params), REFERENCE_MEASUREMENT_COLUMNS
        )

    def _basis(self, table: str) -> list[Any]:
        return list(self._get("basis", BasisParams(tabelle=table)))

    def _get(self, endpoint: str, params: BaseParams) -> Any:
        rsp = self._client.get(
            f"{self.BASE_URL}/{endpoint}.php",
            params=params.model_dump(exclude_none=True),
        )
        body = rsp.json() if _is_json(rsp.headers.get("content-type")) else None
        error = body.get("fehler") if isinstance(body, dict) else None
        if isinstance(error, dict):
            text = error.get("text", "")
            if rsp.status_code == 200 and text == NO_MATCH:
                return []
            raise ValueError(f"NRW API ({endpoint}): {text} [HTTP {rsp.status_code}]")
        rsp.raise_for_status()
        return body


def _datetime_params(
    component: IdList | None,
    start: datetime,
    end: datetime,
    station: IdList | None,
    method: IdList | None = None,
    matrix: IdList | None = None,
) -> DatetimeMeasurementParams:
    _check_range(start, end)
    return DatetimeMeasurementParams(
        komponente=component,
        beginn=start,
        ende=end,
        station=station,
        methode=method,
        matrix=matrix,
    )


def _check_range(start: date, end: date) -> None:
    # The API rejects an end that is not after start (HTTP 422).
    if isinstance(start, datetime) != isinstance(end, datetime):
        raise TypeError("start and end must both be dates or both datetimes")
    if not start < end:
        raise ValueError(f"end {end} must be after start {start}")


def _is_json(content_type: str | None) -> bool:
    return content_type is not None and "json" in content_type
