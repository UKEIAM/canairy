from .._luftmessnetz._client import LuftmessnetzClient

__all__ = ["BEClient"]


class BEClient(LuftmessnetzClient):
    """Berliner Luftgütemessnetz (BLUME)."""

    BASE_URL = "https://luftdaten.berlin.de/api"
