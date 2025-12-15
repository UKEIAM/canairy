import argparse
import datetime
import pathlib
import pickle
import logging
import sys

from pydantic import BaseModel

from air_pollution.uba import UBAClient


class Component(BaseModel):
    id: int
    code: str
    scope: int


DEFAULT_COMPONENTS = [
    Component(id=1, code="PM10", scope=2),
    Component(id=2, code="CO", scope=4),
    Component(id=3, code="O3", scope=2),
    Component(id=4, code="SO2", scope=2),
    Component(id=5, code="NO2", scope=2),
    Component(id=9, code="PM2", scope=2),
]


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv
    args = _parse_cl(argv)

    if not args.outpath.exists():
        args.outpath.mkdir(parents=True)

    logging.basicConfig(
        filename=str(args.outpath.joinpath("download.log")),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    client = UBAClient()
    download_multi_station(client, **vars(args))

    return 0


def download_multi_station(client, year_start: int, outpath: pathlib.Path) -> None:

    for year in range(year_start, datetime.date.today().year): 
        logging.info(f"New year: {year}")
        date_dir = outpath.joinpath(str(year))
        if not date_dir.exists():
            date_dir.mkdir(parents=True)

        for station in client.get_stations().data:
            logging.info(f"Station: {station.code}")
            station_dir = date_dir.joinpath(f"{station.code}")
            if not station_dir.exists():
                station_dir.mkdir()
            for component in DEFAULT_COMPONENTS:
                logging.info(f"Component: {component.code}")
                res = client.get_measures(
                    datetime.datetime(year, 1, 1, 0, 0),
                    datetime.datetime(year+1, 12, 31, 23, 0),
                    station.id,
                    component.id,
                    component.scope,
                )
                fname = station_dir.joinpath(f"{component.code}_{component.scope}.pkl")
                with fname.open("wb") as file:
                    pickle.dump(res.model_dump(mode="json"), file)


def _parse_cl(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--year-start", type=int, default=2016)
    parser.add_argument("outpath", type=pathlib.Path)
    return parser.parse_args(argv[1:])


def _int_or_str(val: str) -> int | str:
    try:
        return int(val)
    except ValueError:
        return val
