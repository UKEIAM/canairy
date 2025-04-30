__all__ = ["components", "clf_bins", "clf_thresholds", "ratings"]


components = ("no2_1h", "so2_1h", "o3_1h", "co_8hg", "pm10_24hg")

ratings = {
    1: "sehr gut",
    2: "gut",
    3: "befriedigend",
    4: "ausreichend",
    5: "schlecht",
    6: "sehr schlecht",
}

clf_bins = {
    "no2_1h": [25, 50, 100, 200, 500],
    "so2_1h": [25, 50, 120, 350, 1000],
    "o3_1h": [33, 65, 120, 180, 240],
    "co_8hg": [1, 2, 4, 10, 30],
    "pm10_24hg": [10, 20, 35, 50, 100],
}

clf_thresholds = {
    "no2_1h": 200,
    "so2_1h": 350,
    "o3_1h": 180,
    "co_8hg": 10,
    "pm10_24hg": 50,
}
