from typing import Literal


# 12mg (12-month moving mean, Berlin only) is monthly and starts 2019-01.
Periods_T = Literal[
    "1h", "24h", "8hg", "24hg", "1m", "12mg", "1y", "1yaot40", "5yaot40"
]

TimeSpans_T = Literal[
    "currentday",
    "currentmonth",
    "currentyear",
    "lastday",
    "lastweek",
    "lastmonth",
    "lastyear",
    "all",
    "custom",
]

StationGroup_T = Literal[
    "all",
    "background",
    "industrial",
    "meteorology",
    "ozone",
    "special",
    "suburb",
    "traffic",
    "pollution",
]

GroupCodes_T = Literal["meteorology", "pollution"]
