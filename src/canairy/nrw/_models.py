"""Params and response models for the LANUK API (luftqualitaet.nrw.de/api).

Documented at https://luftqualitaet.nrw.de/apidoku.php. Measurement endpoints
return rows as positional arrays; the column order per endpoint is taken from
that documentation and checked against the row length.
"""

from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, Self
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    field_serializer,
    model_validator,
)

BERLIN = ZoneInfo("Europe/Berlin")
# The API reads and writes all times in CET (UTC+1), also in summer.
CET = timezone(timedelta(hours=1))

# `datetime`/`date` fields shadow the types inside some class bodies.
_DateTime = datetime
_Date = date

IdList = int | Sequence[int]


# --- request params -----------------------------------------------------------


def _join(value: Any) -> Any:
    """Join ids (or years) to the comma-separated list the API expects."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return ",".join(str(v) for v in value)


def to_cet(dt: datetime) -> datetime:
    """Convert to naive CET; naive input is taken as German local time."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BERLIN)
    return dt.astimezone(CET).replace(tzinfo=None)


Ids = Annotated[str | None, BeforeValidator(_join)]


class BaseParams(BaseModel):
    pass


class BasisParams(BaseParams):
    tabelle: str


class FilterParams(BaseParams):
    station: Ids = None
    komponente: Ids = None
    aggregation: Ids = None
    methode: Ids = None
    matrix: Ids = None


class StationParams(FilterParams):
    stationkuerzel: Ids = None
    eucode: Ids = None
    stationsklasse: Ids = None
    stationsumgebung: Ids = None
    komponentenliste: str


class DateRangeParams(BaseParams):
    beginn: date | None = None
    ende: date | None = None

    @field_serializer("beginn", "ende")
    def _date(self, d: _Date) -> str:
        return d.strftime("%Y-%m-%d")


class LimitsParams(FilterParams, DateRangeParams):
    pass


class DateMeasurementParams(FilterParams, DateRangeParams):
    pass


class DatetimeMeasurementParams(FilterParams):
    beginn: datetime | None = None
    ende: datetime | None = None

    @field_serializer("beginn", "ende")
    def _datetime(self, dt: _DateTime) -> str:
        return to_cet(dt).strftime("%Y-%m-%dT%H:%M")


class YearParams(FilterParams):
    jahr: Ids


class OzoneWarningParams(BaseParams):
    bezugszeit: date | None = None

    @field_serializer("bezugszeit")
    def _date(self, d: _Date) -> str:
        return d.strftime("%Y-%m-%d")


# --- metadata -----------------------------------------------------------------


class Component(BaseModel):
    id: Annotated[int, Field(validation_alias="kmpkey")]
    code: Annotated[str, Field(validation_alias="kmpkrz")]
    name: Annotated[str, Field(validation_alias="kmpname")]
    group: Annotated[str, Field(validation_alias="kmpgrp")]


class Method(BaseModel):
    id: Annotated[int, Field(validation_alias="metkey")]
    name: Annotated[str, Field(validation_alias="metname")]
    description: Annotated[str | None, Field(validation_alias="metdescr")]


class Matrix(BaseModel):
    id: Annotated[int, Field(validation_alias="matkey")]
    name: Annotated[str, Field(validation_alias="matname")]
    description: Annotated[str | None, Field(validation_alias="matdescr")]


class Unit(BaseModel):
    id: Annotated[int, Field(validation_alias="einkey")]
    name: Annotated[str, Field(validation_alias="einname")]
    # Reference temperature (°C) and pressure (hPa) of the unit, or
    # "variabel"/"kein".
    reference_temperature: Annotated[int | str, Field(validation_alias="tempbez")]
    reference_pressure: Annotated[int | str, Field(validation_alias="persbez")]


class Aggregation(BaseModel):
    id: Annotated[int, Field(validation_alias="aggkey")]
    name: Annotated[str, Field(validation_alias="aggname")]
    # AVG, gAVG (moving average), SUM, MAX, UEBG (exceedance count).
    type: Annotated[str, Field(validation_alias="aggtyp")]
    # Base interval and covered period: H, 8H, T (day), 4T, M, J (year), …
    interval: Annotated[str, Field(validation_alias="aggzeit")]
    period: Annotated[str, Field(validation_alias="aggzeitraum")]


class Availability(BaseModel):
    """Data availability of one series (station × component × … × aggregation)."""

    station: Annotated[int | None, Field(validation_alias="mstkey")] = None
    component: Annotated[int, Field(validation_alias="kmpkey")]
    matrix: Annotated[int, Field(validation_alias="matkey")]
    method: Annotated[int, Field(validation_alias="metkey")]
    # Only in station component lists.
    unit: Annotated[int | None, Field(validation_alias="einkey")] = None
    aggregation: Annotated[int, Field(validation_alias="aggkey")]
    # Start of the first and last interval with data.
    start: Annotated[date, Field(validation_alias="datenstart")]
    end: Annotated[date, Field(validation_alias="datenende")]


class Station(BaseModel):
    id: Annotated[int, Field(validation_alias="mstkey")]
    code: Annotated[str, Field(validation_alias="mstkrz")]
    name: Annotated[str, Field(validation_alias="mstname")]
    # "Hintergrund", "Industrie", "Verkehr"
    station_class: Annotated[str, Field(validation_alias="mstklasse")]
    environment: Annotated[str, Field(validation_alias="mstumgebung")]
    # Missing for many special-purpose (e.g. passive sampler) sites.
    eu_code: Annotated[str | None, Field(validation_alias="msteucode")]
    postal_code: Annotated[int, Field(validation_alias="mstplz")]
    street: Annotated[str, Field(validation_alias="mststrasse")]
    city: Annotated[str, Field(validation_alias="mstort")]
    # Metres above sea level.
    altitude: Annotated[int | None, Field(validation_alias="msthoehe")]
    # UTM zone 32N (ETRS89, EPSG:25832) easting/northing in metres.
    utm_east: Annotated[int, Field(validation_alias="mste32")]
    utm_north: Annotated[int, Field(validation_alias="mstn32")]
    description: Annotated[str | None, Field(validation_alias="mstbeschreibung")]
    # Only with `include_components=True`.
    components: Annotated[
        list[Availability] | None, Field(validation_alias="mstkomponenten")
    ] = None


# --- rows ---------------------------------------------------------------------


def parse_cet(value: Any) -> Any:
    """Parse ``YYYY-MM-DD hh:mm:ss`` to an aware CET (UTC+1) datetime.

    Kept in CET rather than converted to Europe/Berlin, so day and month
    boundaries stay at midnight, as the API defines them.
    """
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CET)
    return value


CETDatetime = Annotated[datetime, BeforeValidator(parse_cet)]


class RowModel(BaseModel):
    @classmethod
    def from_rows(cls, rows: list[Any], columns: Sequence[str]) -> list[Self]:
        return [cls.from_row(row, columns) for row in rows]

    @classmethod
    def from_row(cls, row: Any, columns: Sequence[str]) -> Self:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ValueError(
                f"Unexpected row {row!r}: expected {len(columns)} columns {columns}"
            )
        return cls(**dict(zip(columns, row, strict=True)))


class Measurement(RowModel):
    station: int
    component: int
    matrix: int
    method: int
    unit: int
    # Interval start and end.
    start: CETDatetime
    end: CETDatetime
    # Reference period of monthly ("2026-01"), yearly ("2025") and daily
    # 8-hour maxima ("2026-11-20"); None for the other endpoints.
    reference: str | None = None
    # None if below the detection limit (or missing).
    value: float | None
    # The measured value without applying the detection limit.
    raw_value: float | None
    detection_limit: float | None
    below_detection_limit: bool = False
    # False while provisional.
    validated: bool

    @model_validator(mode="before")
    @classmethod
    def _below_limit(cls, data: Any) -> Any:
        # The API reports values below the detection limit as "<limit".
        value = data.get("value") if isinstance(data, dict) else None
        if isinstance(value, str) and value.startswith("<"):
            return {**data, "value": None, "below_detection_limit": True}
        return data


_BASE = ("station", "component", "matrix", "method", "unit", "start", "end")
_VALUES = ("value", "raw_value", "detection_limit", "validated")
MEASUREMENT_COLUMNS = (*_BASE, *_VALUES)
REFERENCE_MEASUREMENT_COLUMNS = (*_BASE, "reference", *_VALUES)


class ExceedanceDays(RowModel):
    """Number of days with a PM10 daily mean above 50 µg/m³."""

    station: int
    matrix: int
    method: int
    unit: int
    start: CETDatetime
    # End of the counted period; before the year's end for the current year.
    end: CETDatetime
    year: str
    count: int
    validated: bool


EXCEEDANCE_COLUMNS = (
    "station", "matrix", "method", "unit", "start", "end", "year", "count", "validated"
)


class AirQualityIndex(RowModel):
    """Hourly air-quality index of one pollutant (1 very good … 6 very bad)."""

    station: int
    component: int
    matrix: int
    method: int
    aggregation: int
    start: CETDatetime
    end: CETDatetime
    reference: CETDatetime
    index: int
    text: str
    validated: bool


AQI_COLUMNS = (
    "station", "component", "matrix", "method", "aggregation",
    "start", "end", "reference", "index", "text", "validated",
)


class TotalAirQualityIndex(RowModel):
    """Hourly overall index: the worst of PM10, PM2.5, NO2, SO2 and O3."""

    station: int
    start: CETDatetime
    end: CETDatetime
    reference: CETDatetime
    index: int
    text: str
    # Components that determine the index.
    components: list[int]
    # True if the substitute ozone value (mean over all ozone stations, for
    # stations without ozone) determines the index.
    ozone_substitute: bool
    ozone_substitute_stations: int
    validated: bool


TOTAL_AQI_COLUMNS = (
    "station", "start", "end", "reference", "index", "text", "components",
    "ozone_substitute", "ozone_substitute_stations", "validated",
)


class OzoneWarning(RowModel):
    """Ozone threshold message for NRW (0 none expected … 5 alert measured)."""

    day: date
    level: int
    text: str
    validated: bool


OZONE_WARNING_COLUMNS = ("day", "level", "text", "validated")
