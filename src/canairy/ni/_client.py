import json
from typing import ClassVar

from .._http import build_client
from ._models import Data

__all__ = ["NIClient"]


class NIClient:
    """Lufthygienisches Überwachungssystem Niedersachsen (LÜN).

    LÜN publishes no queryable API, only one documented JSON file with the
    hourly values of all stations over the last 30 days, updated hourly.
    """

    URL: ClassVar[str] = "https://www.luen-ni.de/json30m.txt"

    def __init__(self) -> None:
        self._client = build_client()

    def get_data(self) -> Data:
        """Fetch and parse the 30-day feed (about 1 MB)."""
        rsp = self._client.get(self.URL).raise_for_status()
        # Served as text/plain without a charset; the content is latin-1.
        return Data.from_response(json.loads(rsp.content.decode("latin-1")))
