import datetime
from typing import Literal


Usage = Literal["airquality", "measure", "transgression", "annualbalance", "map"] | None

Language = Literal["de", "en"] | None
Index = Literal["id", "code"] | None

Timestamp = datetime.datetime | datetime.date | None

StrDict = dict[str, str]
