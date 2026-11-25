from .._luftmessnetz._client import LuftmessnetzClient

__all__ = ["HHClient"]


class HHClient(LuftmessnetzClient):
    """Hamburger Luftmessnetz."""

    BASE_URL = "https://hamburg.luftmessnetz.de/api"
