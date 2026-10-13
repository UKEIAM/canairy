import datetime
from typing import Any

from .networks import UBANetwork
from .stations import Station


def filter_stations_by_network(
    stations: list[Station], networks: list[UBANetwork], query: int | str | UBANetwork
) -> list[Station]:
    out = []
    if isinstance(query, str) and len(query) == 2:
        query = query.upper()
    for station in stations:
        for field in UBANetwork.model_fields.keys():
            if getattr(station.network, field) == query:
                out.append(station)

    return out


def filter_stations_active(
    stations: list[Station],
    date_from: str | datetime.date,
    date_to: str | datetime.date,
) -> list[Station]:
    if not isinstance(date_from, datetime.date):
        date_from = datetime.date.fromisoformat(date_from)

    if not isinstance(date_to, datetime.date):
        date_to = datetime.date.fromisoformat(date_to)

    out = []
    for station in stations:
        start = station.active_from <= date_from
        stop = True if station.active_to is None else station.active_to >= date_to
        if start and stop:
            out.append(station)

    return out


def unpack(indices: list[str] | dict[str, Any]) -> list[str]:
    """Unpack nested response indices."""
    if isinstance(indices, dict):
        for val in indices.values():
            res = unpack(val)
        return res
    elif isinstance(indices, list):
        return indices
    else:
        raise TypeError(f"Unhandled type {type(indices)} in indices.")


def normalize_response_indices(indices: dict[str, Any]) -> list[str]:
    """Normalize case and whitespace."""
    return [item.lower().replace(" ", "_") for item in unpack(indices)]
