import datetime

from .networks import Network
from .stations import Station


def filter_stations_by_network(
    stations: list[Station], networks: list[Network], query: int | str | Network
) -> list[Station]:
    out = []
    for station in stations:
        for field in Network.model_fields.keys():
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
