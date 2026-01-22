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
