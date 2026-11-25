"""Models for the LÜN 30-day JSON feed (``json30m.txt``).

The feed is documented in the appendix of "Erläuterungen und Hinweise zu den
LÜN-Daten" (https://www.umwelt.niedersachsen.de/download/60236). Numbers are
strings with a decimal comma; values are hourly and oldest first.
"""

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated, Any, Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, BeforeValidator, Field

__all__ = [
    "BERLIN",
    "Component",
    "Data",
    "Series",
    "Station",
    "Value",
    "parse_number",
]

BERLIN = ZoneInfo("Europe/Berlin")

# `Value.datetime` shadows the type inside the class body.
_DateTime = datetime

MISSING = "***"
BELOW_LIMIT_PREFIX = "<"


def parse_number(raw: str) -> float:
    """Parse a number with a decimal comma (``"52,22694"``)."""
    return float(raw.replace(",", "."))


DecimalComma = Annotated[float, BeforeValidator(parse_number)]


class Component(BaseModel):
    code: Annotated[str, Field(validation_alias="kennung")]
    name: str
    unit: Annotated[str, Field(validation_alias="einheit")]
    # Averaging period in words, e.g. "Einstundenmittelwert".
    averaging: Annotated[str, Field(validation_alias="zeitbezug")]


class Station(BaseModel):
    code: Annotated[str, Field(validation_alias="kennung")]
    code_eu: Annotated[str, Field(validation_alias="EOI-Kennung")]
    name: str
    location: Annotated[str, Field(validation_alias="ort")]
    street: Annotated[str, Field(validation_alias="strasse")]
    lat: DecimalComma
    lng: DecimalComma
    # Metres above sea level.
    altitude: Annotated[DecimalComma, Field(validation_alias="hoehe")]
    # Classification after the IPR guidance: area ("städtisch", "vorstädtisch",
    # "ländlich") and station type ("Hintergrund", "Verkehr", "Industrie").
    area: Annotated[str, Field(validation_alias="gebiet")]
    type: Annotated[str, Field(validation_alias="art")]
    representativeness: Annotated[str, Field(validation_alias="repraesentativitaet")]

    @classmethod
    def from_response(cls, item: dict[str, Any]) -> Self:
        coords = item["koordinaten"]
        return cls(**item, lat=coords["breite"], lng=coords["laenge"])


class Value(BaseModel):
    """One hourly value; `datetime` is the end of its averaging interval."""

    datetime: datetime
    # None if missing or below the detection limit.
    value: float | None
    # Set if the value is below this detection limit ("<0,6" in the feed).
    detection_limit: float | None = None

    @classmethod
    def from_raw(cls, dt: _DateTime, raw: str) -> Self:
        if raw == MISSING:
            return cls(datetime=dt, value=None)
        if raw.startswith(BELOW_LIMIT_PREFIX):
            limit = parse_number(raw.removeprefix(BELOW_LIMIT_PREFIX))
            return cls(datetime=dt, value=None, detection_limit=limit)
        return cls(datetime=dt, value=parse_number(raw))


class Series(BaseModel):
    """The 30-day history of one component at one station."""

    station: str
    component: str
    # Current air-quality index of a pollutant (<= 2 very good, > 6 very bad);
    # None for meteorological components and if there is no current value.
    air_quality: float | None
    values: list[Value]


class Data(BaseModel):
    """The complete feed."""

    network: str
    # Time of the newest value, as published (end of its interval).
    timestamp: datetime
    comments: list[str]
    history: list[str]
    components: list[Component]
    stations: list[Station]
    series: list[Series]

    def get_series(self, station: str, component: str) -> Series:
        """Return the series of `component` at `station` (codes, case-sensitive)."""
        for s in self.series:
            if s.station == station and s.component == component:
                return s
        raise KeyError((station, component))

    @classmethod
    def from_response(cls, result: dict[str, Any]) -> Self:
        timestamp = parse_timestamp(result["datum"], result["zeit"], result["zeitzone"])
        series = [
            _parse_series(station["kennung"], item, timestamp)
            for station in result["messwerte"]
            for item in station["messstellen"]
        ]
        return cls(
            network=result["messnetz"],
            timestamp=timestamp,
            comments=result.get("kommentar", []),
            history=result.get("Dateihistorie", []),
            components=[Component(**item) for item in result["komponenten"]],
            stations=[Station.from_response(item) for item in result["stationen"]],
            series=series,
        )


_ZONE = re.compile(r"UTC([+-]\d{1,2})h")


def parse_timestamp(date: str, time: str, zone: str) -> datetime:
    """Parse the feed timestamp (local time with an offset like ``UTC+1h``)."""
    match = _ZONE.fullmatch(zone.strip())
    if match is None:
        raise ValueError(f"Unknown time zone {zone!r}")
    tz = timezone(timedelta(hours=int(match[1])))
    naive = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
    return naive.replace(tzinfo=tz).astimezone(BERLIN)


def _parse_series(station: str, item: dict[str, Any], timestamp: datetime) -> Series:
    raw_values = item["verlauf"]
    n = len(raw_values)
    # The newest value is last and belongs to the feed timestamp. Step back in
    # UTC so the hours stay evenly spaced across DST changes.
    end = timestamp.astimezone(UTC)
    values = [
        Value.from_raw((end - timedelta(hours=n - 1 - i)).astimezone(BERLIN), raw)
        for i, raw in enumerate(raw_values)
    ]
    raw_aq = item.get("luftqualitaet")
    # "0,00" marks a pollutant without a current value.
    air_quality = parse_number(raw_aq) if raw_aq is not None else None
    if air_quality == 0:
        air_quality = None
    return Series(
        station=station,
        component=item["kennung"],
        air_quality=air_quality,
        values=values,
    )
